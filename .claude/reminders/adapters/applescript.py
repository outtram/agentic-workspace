import subprocess
from datetime import datetime, timedelta
from typing import Optional


class AppleScriptAdapter:
    """Interface to macOS Reminders.app via AppleScript"""

    def __init__(self, timeout: int = 120):
        self.timeout = timeout
        self._per_list_timeout = 60  # per-list query timeout

    def create_reminder(
        self,
        name: str,
        body: str = "",
        tags: Optional[list[str]] = None,
        due_date: Optional[str] = None,
        priority: int = 0,
        list_name: str = "Reminders"
    ) -> str:
        """Create reminder and return Apple reminder ID"""
        # Embed tags as hashtags in the body (Reminders.app doesn't support tags property)
        tag_hashtags = " ".join(f"#{tag}" for tag in (tags or []))
        full_body = f"{body}\n\n{tag_hashtags}".strip() if tag_hashtags else body

        script = f'''
tell application "Reminders"
    tell list "{list_name}"
        set newReminder to make new reminder
        set name of newReminder to "{self._escape(name)}"
        set body of newReminder to "{self._escape(full_body)}"
        set priority of newReminder to {priority}
        '''

        if due_date:
            script += f'set due date of newReminder to date "{due_date}"\n'

        script += '''
        return id of newReminder
    end tell
end tell
'''

        result = self._execute(script)
        return result.strip()

    def update_reminder(self, reminder_id: str, **changes):
        """Update reminder fields"""
        updates = []

        if "name" in changes:
            updates.append(f'set name of theReminder to "{self._escape(changes["name"])}"')

        if "body" in changes:
            updates.append(f'set body of theReminder to "{self._escape(changes["body"])}"')

        # Note: tags are handled as hashtags in body, not as a separate property

        if "priority" in changes:
            updates.append(f'set priority of theReminder to {changes["priority"]}')

        if "completed" in changes:
            updates.append(f'set completed of theReminder to {str(changes["completed"]).lower()}')

        script = f'''
tell application "Reminders"
    set theReminder to reminder id "{reminder_id}"
    {chr(10).join(updates)}
end tell
'''

        self._execute(script)

    def delete_reminder(self, reminder_id: str):
        """Delete reminder"""
        script = f'''
tell application "Reminders"
    delete reminder id "{reminder_id}"
end tell
'''
        self._execute(script)

    def _get_list_names(self) -> list[str]:
        """Get all reminder list names (fast — no iteration)."""
        script = 'tell application "Reminders" to return name of every list'
        result = self._execute(script)
        return [n.strip() for n in result.strip().split(", ") if n.strip()]

    def fetch_recent_reminders(self, since_days: int = 1) -> list[dict]:
        """Fetch only reminders created in the last N days.

        Queries each list individually to avoid timeouts on large
        Reminders databases. Skips lists that time out and continues.
        Filters by creation date in Python (bulk fetch is faster).
        """
        cutoff = datetime.now() - timedelta(days=since_days)
        all_reminders: list[dict] = []
        for list_name in self._get_list_names():
            try:
                result = self._fetch_from_list(list_name)
                parsed = self._parse_reminders(result)
                # Filter by creation date in Python
                for r in parsed:
                    created = r.get("created")
                    if created and created >= cutoff:
                        all_reminders.append(r)
                    elif not created:
                        # If no creation date, include it (can't filter)
                        all_reminders.append(r)
            except (TimeoutError, RuntimeError):
                continue
        return all_reminders

    def _fetch_from_list(self, list_name: str) -> str:
        """Fetch all active reminders from a single list using fast bulk access.

        Uses `properties of` which is dramatically faster than iterating
        individual reminders (~8s vs 85s+ for 45 items).
        """
        escaped_name = self._escape(list_name)
        script = f'''
tell application "Reminders"
    set fieldSep to (ASCII character 30)
    set recSep to (ASCII character 29)
    tell list "{escaped_name}"
        set allProps to properties of (every reminder whose completed is false)
        set output to ""
        repeat with p in allProps
            set rId to id of p
            set rName to name of p
            set rBody to body of p
            if rBody is missing value then set rBody to ""
            -- Escape newlines in body
            set {{oldDelims, AppleScript's text item delimiters}} to {{AppleScript's text item delimiters, return}}
            set bodyParts to text items of rBody
            set AppleScript's text item delimiters to "\\\\n"
            set rBody to bodyParts as string
            set AppleScript's text item delimiters to oldDelims
            set rPri to priority of p
            try
                set rDueDate to due date of p as string
            on error
                set rDueDate to ""
            end try
            try
                set cDate to creation date of p as string
            on error
                set cDate to ""
            end try
            set output to output & "{escaped_name}" & fieldSep & rId & fieldSep & rName & fieldSep & rBody & fieldSep & rDueDate & fieldSep & rPri & fieldSep & cDate & recSep
        end repeat
    end tell
    return output
end tell
'''
        return self._execute_with_timeout(script, self._per_list_timeout)

    def fetch_all_reminders(self) -> list[dict]:
        """Fetch all active (non-completed) reminders.

        Queries each list individually to avoid timeouts.
        """
        all_reminders: list[dict] = []
        for list_name in self._get_list_names():
            try:
                result = self._fetch_from_list(list_name)
                all_reminders.extend(self._parse_reminders(result))
            except (TimeoutError, RuntimeError):
                continue
        return all_reminders

    def _execute_with_timeout(self, script: str, timeout: int) -> str:
        """Execute AppleScript with a specific timeout."""
        try:
            result = subprocess.run(
                ['osascript', '-e', script],
                capture_output=True,
                text=True,
                timeout=timeout
            )
            if result.returncode != 0:
                raise RuntimeError(f"AppleScript error: {result.stderr}")
            return result.stdout
        except subprocess.TimeoutExpired:
            raise TimeoutError(f"AppleScript timed out after {timeout}s")

    def _execute(self, script: str) -> str:
        """Execute AppleScript and return output"""
        try:
            result = subprocess.run(
                ['osascript', '-e', script],
                capture_output=True,
                text=True,
                timeout=self.timeout
            )

            if result.returncode != 0:
                raise RuntimeError(f"AppleScript error: {result.stderr}")

            return result.stdout
        except subprocess.TimeoutExpired:
            raise TimeoutError(f"AppleScript timed out after {self.timeout}s")

    def _escape(self, text: str) -> str:
        """Escape quotes in text for AppleScript"""
        return text.replace('"', '\\"')

    def _parse_reminders(self, output: str) -> list[dict]:
        """Parse reminder data using ASCII control character delimiters.

        Fields separated by ␞ (ASCII 30), records separated by ␝ (ASCII 29).
        Supports 6-field (legacy) and 7-field (with creation date) formats.
        """
        import re

        reminders = []
        field_sep = chr(30)
        record_sep = chr(29)

        for record in output.strip().split(record_sep):
            record = record.strip()
            if not record:
                continue

            parts = record.split(field_sep)
            if len(parts) == 7:
                list_name, rid, name, body, due_date, priority, created_str = parts
            elif len(parts) == 6:
                list_name, rid, name, body, due_date, priority = parts
                created_str = ""
            else:
                continue

            body = body.replace("\\n", "\n")
            tags = re.findall(r'#(\w+)', body)

            try:
                pri = int(priority)
            except ValueError:
                pri = 0

            created_dt = self._parse_datetime(created_str)

            reminders.append({
                "id": rid,
                "name": name,
                "body": body,
                "tags": tags,
                "due_date": self._parse_date(due_date),
                "priority": pri,
                "list": list_name,
                "completed": False,
                "modified": datetime.now(),
                "created": created_dt,
            })

        return reminders

    def _parse_datetime(self, date_str: str) -> Optional[datetime]:
        """Parse AppleScript datetime string to datetime object."""
        if not date_str or date_str == "missing value":
            return None
        try:
            parts = date_str.split(" at ")
            date_part = parts[0]
            time_part = parts[1] if len(parts) > 1 else "12:00:00 am"
            dt_str = f"{date_part} {time_part}"
            return datetime.strptime(dt_str, "%A, %d %B %Y %I:%M:%S %p")
        except (ValueError, IndexError):
            return None

    def _parse_date(self, date_str: str) -> Optional[str]:
        """Parse AppleScript date string to YYYY-MM-DD"""
        if not date_str or date_str == "missing value":
            return None

        try:
            # "Thursday, 12 February 2026 at 12:00:00 am"
            parts = date_str.split(" at ")[0]
            date_obj = datetime.strptime(parts, "%A, %d %B %Y")
            return date_obj.date().isoformat()
        except (ValueError, IndexError):
            return None
