"""
departments/library/__init__.py
---------------------------------
Ministry of Knowledge — Library Department

Exports the LibraryManager as the department's public interface.
The DepartmentFactory and Orchestrator import from here.
"""

from departments.library.library_manager import LibraryManager

__all__ = ["LibraryManager"]
