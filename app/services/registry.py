from __future__ import annotations

import asyncio
import logging

from app.core.config import settings
from app.schemas.scan import RegistryCredentials

log = logging.getLogger(__name__)


class RegistryError(RuntimeError):
    pass


class RegistryService:
    def build_remote_tag(self, local_image: str, creds: RegistryCredentials) -> str:
        image_name = local_image.split("/")[-1]
        return f"{creds.url}/{creds.project}/{image_name}"

    async def push(self, local_image: str, creds: RegistryCredentials) -> str:
        remote_image = self.build_remote_tag(local_image, creds)
        log.info("Registry push | %s → %s", local_image, remote_image)

        await self._login(creds)
        try:
            await self._tag(local_image, remote_image)
            await self._push(remote_image)
        finally:
            await self._logout(creds.url)

        return remote_image

    async def _login(self, creds: RegistryCredentials) -> None:
        log.debug("docker login | url=%s username=%s", creds.url, creds.username)
        await self._run(
            ["docker", "login", creds.url, "--username", creds.username, "--password-stdin"],
            stdin=creds.password,
        )
        log.debug("docker login OK")

    async def _tag(self, source: str, target: str) -> None:
        log.debug("docker tag | %s → %s", source, target)
        await self._run(["docker", "tag", source, target])

    async def _push(self, image: str) -> None:
        log.info("docker push | %s", image)
        await self._run(["docker", "push", image])
        log.info("docker push OK | %s", image)

    async def _logout(self, registry_url: str) -> None:
        try:
            await self._run(["docker", "logout", registry_url])
            log.debug("docker logout OK | %s", registry_url)
        except RegistryError:
            pass

    async def _run(self, cmd: list[str], stdin: str | None = None) -> str:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdin=asyncio.subprocess.PIPE if stdin else None,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdin_bytes = stdin.encode() if stdin else None
        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(input=stdin_bytes),
                timeout=settings.process_timeout,
            )
        except asyncio.TimeoutError as exc:
            process.kill()
            await process.wait()
            raise RegistryError(f"Timeout: {' '.join(cmd[:2])}") from exc

        out = stdout.decode("utf-8", errors="replace").strip()
        err = stderr.decode("utf-8", errors="replace").strip()

        if process.returncode != 0:
            log.error("Ошибка %s: %s", " ".join(cmd[:2]), err)
            raise RegistryError(f"Ошибка `{' '.join(cmd[:2])}`: {err}")

        return out

registry_service = RegistryService()