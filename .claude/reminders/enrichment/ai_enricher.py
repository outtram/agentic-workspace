"""AI-powered task enrichment for making vague todos actionable"""

import re
from typing import Optional, Dict, List
from datetime import datetime


class TaskEnricher:
    """Enriches vague tasks with better titles, steps, and context"""

    def __init__(self):
        # Patterns that indicate vague tasks
        self.vague_patterns = [
            r'^(check|look|review|follow up|chase|contact)\s+\w+$',  # "check phil", "follow up mel"
            r'^\w+\s+(thing|stuff|item)$',  # "phil thing", "mel stuff"
            r'^[a-z\s]{3,15}$',  # Very short, lowercase only
            r'\bmeet\s+\w+$',  # "meet phil" without context
        ]

        # Context clues from common patterns
        self.context_hints = {
            'survey': {'tags': ['#admin', '#form'], 'urgency': 'medium'},
            'meeting': {'tags': ['#meeting', '#calendar'], 'steps': ['Check calendar', 'Send invite']},
            'call': {'tags': ['#phone', '#meeting'], 'steps': ['Check availability', 'Schedule call']},
            'chase': {'tags': ['#followup', '#urgent'], 'urgency': 'high'},
            'review': {'tags': ['#review', '#check'], 'steps': ['Review details', 'Provide feedback']},
            'email': {'tags': ['#email', '#communication'], 'steps': ['Draft email', 'Send']},
        }

    def is_vague(self, title: str, description: str = "") -> bool:
        """Check if a task title is vague and needs enrichment"""
        if len(title) < 10:  # Very short titles are likely vague
            return True

        # Check for missing or placeholder descriptions
        placeholder_descriptions = [
            "", "missing value", "no description", "no description provided",
            "## description", "context, references, considerations.",
            "review task details"
        ]
        if description.strip().lower() in placeholder_descriptions:
            return True

        # Check title patterns
        for pattern in self.vague_patterns:
            if re.search(pattern, title.lower()):
                return True

        # Check for meetings without clear agenda/outcome
        if re.search(r'\b(meet|meeting|call|catch up|chat)\b', title.lower()):
            # Meetings are vague unless they have specific context
            has_context = any(word in title.lower() for word in ['about', 'regarding', 'discuss', 'review', 'planning', 'demo'])
            # Also check if description has actual content (not just boilerplate)
            desc_has_content = len(description) > 50 and not any(
                placeholder in description.lower()
                for placeholder in ['no description', 'review task details', 'complete task']
            )
            if not has_context and not desc_has_content:
                return True

        return False

    def extract_context_hints(self, title: str, description: str = "") -> Dict:
        """Extract context hints from title and description"""
        hints = {'tags': [], 'steps': [], 'urgency': 'medium'}

        text = f"{title} {description}".lower()

        for keyword, context in self.context_hints.items():
            if keyword in text:
                hints['tags'].extend(context.get('tags', []))
                hints['steps'].extend(context.get('steps', []))
                if 'urgency' in context:
                    hints['urgency'] = context['urgency']

        # Remove duplicates
        hints['tags'] = list(set(hints['tags']))
        hints['steps'] = list(set(hints['steps']))

        return hints

    def suggest_enrichment(self, title: str, description: str = "",
                          due_date: Optional[str] = None) -> Dict:
        """Generate enrichment suggestions for a vague task"""

        if not self.is_vague(title, description):
            return {'needs_enrichment': False}

        hints = self.extract_context_hints(title, description)

        # Build enrichment suggestion
        enrichment = {
            'needs_enrichment': True,
            'original_title': title,
            'vague_reason': self._explain_vagueness(title, description),
            'suggested_improvements': {
                'title_questions': self._generate_clarifying_questions(title),
                'suggested_tags': hints['tags'],
                'suggested_steps': hints['steps'] if hints['steps'] else [
                    'Clarify what needs to be done',
                    'Identify next action',
                    'Complete task'
                ],
                'urgency_hint': hints['urgency']
            }
        }

        return enrichment

    def _explain_vagueness(self, title: str, description: str = "") -> str:
        """Explain why a title is considered vague"""
        if len(title) < 10:
            return "Title is very short and lacks specific action"

        if description.strip() in ["", "missing value", "No description"]:
            return "Description is missing or placeholder text"

        if re.search(r'^\w+\s+(thing|stuff)$', title.lower()):
            return "Uses placeholder words like 'thing' or 'stuff'"

        if re.search(r'^(check|review|look)\s+\w+$', title.lower()):
            return "Lacks specific action or outcome"

        if re.search(r'\b(meet|meeting|call|catch up|chat)\b', title.lower()):
            return "Meeting without clear agenda or desired outcome"

        return "Title could be more specific about what needs to be done"

    def _generate_clarifying_questions(self, title: str) -> List[str]:
        """Generate questions to help clarify a vague task"""
        questions = []

        # Extract potential person/thing name
        words = title.split()
        if len(words) >= 2:
            subject = words[-1]
            questions.append(f"What specifically needs to be done with {subject}?")
            questions.append(f"What's the desired outcome or next action?")
        else:
            questions.append("What specifically needs to be done?")
            questions.append("What's the next actionable step?")

        questions.append("What context or background is important?")
        questions.append("Who else is involved or needs to be contacted?")

        return questions

    def format_enrichment_prompt(self, enrichment: Dict) -> str:
        """Format enrichment suggestions as a friendly prompt"""
        if not enrichment.get('needs_enrichment'):
            return ""

        prompt = f"\n🤔 **Task looks vague:** \"{enrichment['original_title']}\"\n"
        prompt += f"**Why:** {enrichment['vague_reason']}\n\n"

        prompt += "**Let's make it actionable:**\n"
        for q in enrichment['suggested_improvements']['title_questions']:
            prompt += f"  • {q}\n"

        if enrichment['suggested_improvements']['suggested_tags']:
            prompt += f"\n**Suggested tags:** {' '.join(enrichment['suggested_improvements']['suggested_tags'])}\n"

        if enrichment['suggested_improvements']['suggested_steps']:
            prompt += f"\n**Possible steps:**\n"
            for step in enrichment['suggested_improvements']['suggested_steps']:
                prompt += f"  - [ ] {step}\n"

        return prompt
