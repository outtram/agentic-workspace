import re
import yaml
from pathlib import Path
from datetime import datetime
from typing import Optional
from reminders.core.models import WorkItem


class WorkItemFileAdapter:
    """Read/write work items as markdown files with YAML frontmatter"""

    def __init__(self, work_dir: Path = None):
        if work_dir is None:
            work_dir = Path("/Users/touttram/CODE/AAGLOBAL/.claude/work/tasks")
        self.work_dir = Path(work_dir)
        self.work_dir.mkdir(parents=True, exist_ok=True)

    def create(self, work_item: WorkItem) -> Path:
        """Create work item markdown file"""
        filename = self._generate_filename(work_item)
        file_path = self.work_dir / filename

        content = self._generate_content(work_item)
        file_path.write_text(content)

        return file_path

    def read(self, work_item_id: str) -> Optional[WorkItem]:
        """Read work item from file"""
        file_path = self._find_file(work_item_id)
        if not file_path:
            return None

        content = file_path.read_text()
        frontmatter, body = self._parse_frontmatter(content)

        description = self._extract_description(body)

        return WorkItem(
            id=frontmatter.get("id", ""),
            title=frontmatter.get("title", ""),
            status=frontmatter.get("status", "todo"),
            priority=frontmatter.get("priority", "low"),
            due_date=frontmatter.get("due_date"),
            tags=frontmatter.get("tags", []),
            tag_categories=frontmatter.get("tag_categories", {}),
            eisenhower_quadrant=frontmatter.get("eisenhower_quadrant", "q4"),
            eisenhower_urgent=frontmatter.get("eisenhower_urgent", False),
            eisenhower_important=frontmatter.get("eisenhower_important", False),
            source=frontmatter.get("source", "manual"),
            reminder_id=frontmatter.get("reminder_id"),
            reminder_list=frontmatter.get("reminder_list"),
            branch=frontmatter.get("branch"),
            description=description,
            created=self._parse_datetime(frontmatter.get("created")),
            updated=self._parse_datetime(frontmatter.get("updated"))
        )

    def update(self, work_item: WorkItem):
        """Update existing work item file"""
        file_path = self._find_file(work_item.id)
        if not file_path:
            raise FileNotFoundError(f"Work item {work_item.id} not found")

        work_item.updated = datetime.now()

        content = self._generate_content(work_item)
        file_path.write_text(content)

    def delete(self, work_item_id: str):
        """Delete work item file"""
        file_path = self._find_file(work_item_id)
        if file_path:
            file_path.unlink()

    def list_all(self) -> list[WorkItem]:
        """List all work items"""
        work_items = []
        for file_path in self.work_dir.glob("OUT-*.md"):
            try:
                work_item = self.read(self._extract_id_from_filename(file_path.name))
                if work_item:
                    work_items.append(work_item)
            except (yaml.YAMLError, ValueError) as e:
                # Skip files with malformed YAML or invalid format
                print(f"Warning: Skipping {file_path.name}: {e}")
                continue
        return work_items

    def _generate_filename(self, work_item: WorkItem) -> str:
        """Generate filename from work item"""
        clean_title = work_item.title.lower()[:50]
        clean_title = re.sub(r'[^\w\s-]', '', clean_title)
        clean_title = re.sub(r'[\s_]+', '-', clean_title)
        clean_title = re.sub(r'-+', '-', clean_title).strip('-')

        return f"{work_item.id}-{clean_title}.md"

    def _generate_content(self, work_item: WorkItem) -> str:
        """Generate markdown content with YAML frontmatter"""
        frontmatter = {
            "id": work_item.id,
            "title": work_item.title,
            "type": "task",
            "status": work_item.status,
            "priority": work_item.priority,
            "created": work_item.created.isoformat() if work_item.created else datetime.now().isoformat(),
            "updated": work_item.updated.isoformat() if work_item.updated else datetime.now().isoformat(),
            "branch": work_item.branch,
            "source": work_item.source,
            "eisenhower_quadrant": work_item.eisenhower_quadrant,
            "eisenhower_urgent": work_item.eisenhower_urgent,
            "eisenhower_important": work_item.eisenhower_important,
        }

        if work_item.due_date:
            frontmatter["due_date"] = work_item.due_date

        if work_item.tags:
            frontmatter["tags"] = work_item.tags

        if work_item.tag_categories:
            frontmatter["tag_categories"] = work_item.tag_categories

        if work_item.reminder_id:
            frontmatter["reminder_id"] = work_item.reminder_id

        if work_item.reminder_list:
            frontmatter["reminder_list"] = work_item.reminder_list

        content = "---\n"
        content += yaml.dump(frontmatter, default_flow_style=False, sort_keys=False)
        content += "---\n\n"
        content += f"# {work_item.title}\n\n"
        content += "## Description\n"
        content += work_item.description or "No description provided"
        content += "\n\n"
        content += "## Steps\n"
        if work_item.steps:
            for step in work_item.steps:
                content += f"- [ ] {step}\n"
        else:
            content += "- [ ] Review task details\n"
            content += "- [ ] Complete task\n"
            content += "- [ ] Mark as done\n"

        return content

    def _find_file(self, work_item_id: str) -> Optional[Path]:
        """Find work item file by ID"""
        files = list(self.work_dir.glob(f"{work_item_id}-*.md"))
        return files[0] if files else None

    def _extract_id_from_filename(self, filename: str) -> str:
        """Extract OUT-XXX from filename"""
        match = re.match(r'(OUT-\d+)', filename)
        return match.group(1) if match else ""

    def _parse_frontmatter(self, content: str) -> tuple[dict, str]:
        """Parse YAML frontmatter from markdown"""
        match = re.match(r'^---\n(.*?)\n---\n(.*)$', content, re.DOTALL)
        if not match:
            return {}, content

        frontmatter_text = match.group(1)
        body = match.group(2)

        frontmatter = yaml.safe_load(frontmatter_text)
        return frontmatter, body

    def _extract_description(self, body: str) -> str:
        """Extract description from markdown body"""
        match = re.search(r'## Description\n(.*?)(?:\n##|$)', body, re.DOTALL)
        if match:
            return match.group(1).strip()
        return ""

    def _parse_datetime(self, dt_str) -> Optional[datetime]:
        """Parse ISO datetime string"""
        if not dt_str:
            return None
        try:
            if isinstance(dt_str, datetime):
                return dt_str
            return datetime.fromisoformat(str(dt_str))
        except (ValueError, TypeError):
            return None
