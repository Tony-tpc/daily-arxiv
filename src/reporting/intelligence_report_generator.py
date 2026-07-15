"""Backward-compatible import for the renamed research report generator."""

from .research_report_generator import ResearchReportGenerator


IntelligenceReportGenerator = ResearchReportGenerator

__all__ = ["IntelligenceReportGenerator", "ResearchReportGenerator"]
