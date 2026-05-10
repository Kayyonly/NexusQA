from visual_testing.layout_analyzer import LayoutAnalyzer
from visual_testing.visual_detector import VisualDetector


class ResponsiveAnalyzer:
    def __init__(self) -> None:
        self.visual = VisualDetector()
        self.layout = LayoutAnalyzer()

    async def analyze(self, page) -> dict:
        visual = await self.visual.detect(page)
        layout = await self.layout.analyze(page)
        total_issues = sum(len(visual[k]) for k in ["overflow", "overlap", "hidden", "offscreen"])
        status = "ok" if total_issues == 0 and layout.get("navbar_ok") else "issue_found"
        return {"status": status, "visual_issues": visual, "layout": layout, "total_issues": total_issues}
