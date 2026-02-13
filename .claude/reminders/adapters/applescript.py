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

    def fetch_all_reminders(self) -> list[dict]:
        """Fetch all active (non-completed) reminders"""
        script = '''
tell application "Reminders"
    set output to ""
    repeat with aList in lists
        set listName to name of aList
        repeat with aReminder in reminders of aList
            if completed of aReminder is false then
                set rId to id of aReminder
                set rName to name of aReminder
                try
                    set rBody to body of aReminder
                on error
                    set rBody to ""
                end try
                try
                    set rDueDate to due date of aReminder as string
                on error
                    set rDueDate to ""
                end try
                set rPriority to priority of aReminder
                try
                    set rTags to tags of aReminder
                    set tagStr to ""
                    repeat with aTag in rTags
                        if tagStr is "" then
                            set tagStr to aTag
                        else
                            set tagStr to tagStr & "," & aTag
                        end if
                    end repeat
                on error
                    set tagStr to ""
                end try
                set output to output & listName & "|" & rId & "|" & rName & "|" & rBody & "|" & rDueDate & "|" & rPriority & "|" & tagStr & linefeed
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
        """Parse pipe-delimited reminder data"""
        reminders = []

        for line in output.strip().split('\n'):
            if not line:
                continue

            parts = line.split('|')
            if len(parts) != 7:
                continue

            list_name, rid, name, body, due_date, priority, tags = parts

            reminders.append({
                "id": rid,
                "name": name,
                "body": body,
                "tags": tags.split(',') if tags else [],
                "due_date": self._parse_date(due_date),
                "priority": int(priority),
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
