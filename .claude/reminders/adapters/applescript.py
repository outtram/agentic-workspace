import subprocess
from datetime import datetime
from typing import Optional


class AppleScriptAdapter:
    """Interface to macOS Reminders.app via AppleScript"""

    def __init__(self, timeout: int = 120):
        self.timeout = timeout

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

    def fetch_recent_reminders(self, since_days: int = 1) -> list[dict]:
        """Fetch only reminders created or modified in the last N days.

        Uses AppleScript's `whose` clause for native filtering — Reminders.app
        filters internally without iterating every reminder in our script.
        Much faster than fetch_all_reminders().
        """
        script = f'''
tell application "Reminders"
    set output to ""
    set fieldSep to (ASCII character 30) -- record separator
    set recSep to (ASCII character 29) -- group separator
    set cutoffDate to (current date) - ({since_days} * days)
    repeat with aList in lists
        set listName to name of aList
        try
            set recentOnes to (reminders of aList whose completed is false and modification date > cutoffDate)
        on error
            set recentOnes to {{}}
        end try
        repeat with aReminder in recentOnes
            set rId to id of aReminder
            set rName to name of aReminder
            try
                set rBody to body of aReminder
                set {{oldDelims, AppleScript's text item delimiters}} to {{AppleScript's text item delimiters, return}}
                set bodyParts to text items of rBody
                set AppleScript's text item delimiters to "\\\\n"
                set rBody to bodyParts as string
                set AppleScript's text item delimiters to oldDelims
            on error
                set rBody to ""
            end try
            try
                set rDueDate to due date of aReminder as string
            on error
                set rDueDate to ""
            end try
            set rPriority to priority of aReminder
            set output to output & listName & fieldSep & rId & fieldSep & rName & fieldSep & rBody & fieldSep & rDueDate & fieldSep & rPriority & recSep
        end repeat
    end repeat
    return output
end tell
'''
        result = self._execute(script)
        return self._parse_reminders(result)

    def fetch_all_reminders(self) -> list[dict]:
        """Fetch all active (non-completed) reminders"""
        # Use ␞ (ASCII record separator) as field delimiter and ␟ (unit separator)
        # to replace newlines in body text — pipe + newline breaks parsing when
        # reminder bodies contain URLs or multi-line notes.
        script = '''
tell application "Reminders"
    set output to ""
    set fieldSep to (ASCII character 30) -- record separator ␞
    set recSep to (ASCII character 29) -- group separator ␝
    repeat with aList in lists
        set listName to name of aList
        repeat with aReminder in reminders of aList
            if completed of aReminder is false then
                set rId to id of aReminder
                set rName to name of aReminder
                try
                    set rBody to body of aReminder
                    -- Replace newlines in body so they don't break line parsing
                    set {oldDelims, AppleScript's text item delimiters} to {AppleScript's text item delimiters, return}
                    set bodyParts to text items of rBody
                    set AppleScript's text item delimiters to "\\\\n"
                    set rBody to bodyParts as string
                    set AppleScript's text item delimiters to oldDelims
                on error
                    set rBody to ""
                end try
                try
                    set rDueDate to due date of aReminder as string
                on error
                    set rDueDate to ""
                end try
                set rPriority to priority of aReminder
                set output to output & listName & fieldSep & rId & fieldSep & rName & fieldSep & rBody & fieldSep & rDueDate & fieldSep & rPriority & recSep
            end if
        end repeat
    end repeat
    return output
end tell
'''

        result = self._execute(script)
        return self._parse_reminders(result)

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
        Newlines in body text are escaped as literal \\n.
        """
        import re

        reminders = []
        field_sep = chr(30)  # Record separator
        record_sep = chr(29)  # Group separator

        for record in output.strip().split(record_sep):
            record = record.strip()
            if not record:
                continue

            parts = record.split(field_sep)
            if len(parts) != 6:
                continue

            list_name, rid, name, body, due_date, priority = parts

            # Restore newlines in body
            body = body.replace("\\n", "\n")

            # Extract hashtags from body as tags
            tags = re.findall(r'#(\w+)', body)

            try:
                pri = int(priority)
            except ValueError:
                pri = 0

            reminders.append({
                "id": rid,
                "name": name,
                "body": body,
                "tags": tags,
                "due_date": self._parse_date(due_date),
                "priority": pri,
                "list": list_name,
                "completed": False,
                "modified": datetime.now()
            })

        return reminders

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
