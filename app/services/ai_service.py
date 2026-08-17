import re
from typing import Dict, List, Any
from difflib import SequenceMatcher

# Simple Local NLP Vocabularies for classifying tech areas
CATEGORY_KEYWORDS = {
    "Software Engineering / Web Development": [
        "develop", "code", "programming", "react", "html", "css", "javascript", "python",
        "api", "git", "frontend", "backend", "django", "fastapi", "bug", "framework", 
        "application", "component", "route", "function", "testing", "typescript", "vue"
    ],
    "System Administration / IT Support": [
        "install", "hardware", "printer", "computer", "operating system", "windows", "linux",
        "format", "repair", "driver", "troubleshoot", "pc", "helpdesk", "user", "active directory",
        "server", "ram", "cpu", "disk", "maintenance", "backup"
    ],
    "Networking / Telecommunications": [
        "router", "switch", "ip address", "ping", "cable", "lan", "wan", "packet", "dns",
        "dhcp", "cisco", "subnet", "vlan", "bandwidth", "ethernet", "wifi", "network", "port"
    ],
    "Database Administration": [
        "sql", "database", "query", "mysql", "postgresql", "mongodb", "table", "index",
        "schema", "backup", "migration", "select", "join", "insert", "foreign key", "primary key"
    ],
    "Cybersecurity": [
        "firewall", "encrypt", "decrypt", "exploit", "hack", "penetration", "vulnerability",
        "ssl", "tls", "token", "auth", "hash", "password", "security", "scan", "antivirus"
    ]
}

def clean_text(text: str) -> str:
    if not text:
        return ""
    return re.sub(r"[^\w\s]", "", text.lower()).strip()

class LogbookAIModel:
    @staticmethod
    def evaluate_entry(
        activities: str,
        tools_used: str,
        challenges: str,
        learning_outcome: str,
        previous_entries: List[str] = []
    ) -> Dict[str, Any]:
        suggestions = []
        strengths = []
        
        # 1. Completeness and quality check
        act_len = len(activities.split()) if activities else 0
        tools_len = len(tools_used.split()) if tools_used else 0
        chall_len = len(challenges.split()) if challenges else 0
        out_len = len(learning_outcome.split()) if learning_outcome else 0
        
        score = 0
        
        # Activities scoring (up to 40 pts)
        if act_len >= 30:
            score += 40
            strengths.append("The activities section is highly descriptive.")
        elif act_len >= 15:
            score += 25
            suggestions.append("Consider detailing your daily tasks more extensively in the activities section.")
        elif act_len > 0:
            score += 10
            suggestions.append("The activities description is extremely short. Describe specific projects or tasks completed.")
        else:
            suggestions.append("You must document your weekly activities.")
            
        # Tools used scoring (up to 20 pts)
        if tools_len >= 3:
            score += 20
            strengths.append("You clearly enumerated the tools, libraries, or technologies utilized.")
        elif tools_len > 0:
            score += 10
            suggestions.append("Add the specific versions or exact technologies/frameworks used.")
        else:
            suggestions.append("Specify the tools or resources you utilized this week.")
            
        # Challenges scoring (up to 20 pts)
        if chall_len >= 15:
            score += 20
            strengths.append("You clearly articulated technical blockages or workflow challenges.")
        elif chall_len > 0:
            score += 10
            suggestions.append("Detail how you attempted to debug or overcome challenges.")
        else:
            suggestions.append("Document any challenges, bugs, or blockers experienced, even if resolved.")
            
        # Learning outcome scoring (up to 20 pts)
        if out_len >= 20:
            score += 20
            strengths.append("You highlighted clear personal learning outcomes and skills acquired.")
        elif out_len > 0:
            score += 10
            suggestions.append("Frame your learning outcome around the specific skills you mastered.")
        else:
            suggestions.append("Provide a summary of what you learned or achieved by the end of the week.")

        # 2. Classification
        combined_text = f"{clean_text(activities)} {clean_text(tools_used)} {clean_text(challenges)} {clean_text(learning_outcome)}"
        words = combined_text.split()
        
        best_category = "General IT / Unclassified"
        max_matches = 0
        
        for category, keywords in CATEGORY_KEYWORDS.items():
            matches = sum(1 for word in words if word in keywords)
            if matches > max_matches:
                max_matches = matches
                best_category = category
                
        # 3. Repetition Check
        repetition_flag = False
        if activities and previous_entries:
            curr_cleaned = clean_text(activities)
            for prev in previous_entries:
                prev_cleaned = clean_text(prev)
                # Compute Gestalt pattern matching ratio
                ratio = SequenceMatcher(None, curr_cleaned, prev_cleaned).ratio()
                if ratio > 0.75:
                    repetition_flag = True
                    suggestions.append("Warning: This weekly entry shows a high degree of similarity to a previous submission.")
                    break
                    
        return {
            "completenessScore": min(score, 100),
            "category": best_category,
            "strengths": strengths,
            "suggestions": suggestions,
            "repetitionFlag": repetition_flag,
            "disclaimer": "This feedback is advisory, generated by the local AI Logbook Quality Assistant, and does not replace human supervisor evaluation."
        }

    @staticmethod
    def compare_verification_fields(student_val: str, supervisor_val: str) -> Dict[str, Any]:
        if not student_val or not supervisor_val:
            return {"status": "INSUFFICIENT_INFORMATION", "explanation": "One or both values are missing."}
            
        sv = student_val.strip().lower()
        spv = supervisor_val.strip().lower()
        
        # Exact match
        if sv == spv:
            return {"status": "MATCH", "explanation": "Exact match."}
            
        # Cleaned similarity (e.g. spelling variants, Inc / Ltd, spaces)
        sv_clean = re.sub(r"\b(ltd|limited|inc|incorporated|co|company)\b", "", sv).replace(" ", "")
        spv_clean = re.sub(r"\b(ltd|limited|inc|incorporated|co|company)\b", "", spv).replace(" ", "")
        if sv_clean == spv_clean and len(sv_clean) > 2:
            return {"status": "LIKELY_MATCH", "explanation": "Likely name variation (match after abbreviation normalization)."}
            
        ratio = SequenceMatcher(None, sv, spv).ratio()
        if ratio >= 0.70:
            return {"status": "LIKELY_MATCH", "explanation": f"Likely match with minor spelling variation ({int(ratio*100)}% similarity)."}
            
        return {"status": "MISMATCH", "explanation": f"Significant mismatch detected ({int(ratio*100)}% similarity)."}
