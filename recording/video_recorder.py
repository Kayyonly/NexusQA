from pathlib import Path


class VideoRecorder:
    @staticmethod
    async def finalize_page_video(page) -> str:
        await page.close()
        video = page.video
        if not video:
            return ""
        src = await video.path()
        return str(Path(src))
