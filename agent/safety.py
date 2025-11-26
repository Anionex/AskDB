"""
Safety protocols and risk management for AskDB agent.

This module implements multi-layered safety protocols including:
- Risk classification and assessment
- PII (Personally Identifiable Information) detection
- SQL injection prevention
- Query validation and sanitization
- Automated guardrails and safety checks
"""

import re
import json
import logging
from typing import List, Dict, Any, Optional, Set, Tuple, Union
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime

from config import get_settings


class RiskLevel(Enum):
    """Risk level classification for queries and actions."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class SafetyCheckType(Enum):
    """Types of safety checks."""
    PII_DETECTION = "pii_detection"
    SQL_INJECTION = "sql_injection"
    MALICIOUS_CONTENT = "malicious_content"
    DATA_ACCESS = "data_access"
    QUERY_COMPLEXITY = "query_complexity"
    SENSITIVE_TABLES = "sensitive_tables"
    OUTPUT_FILTERING = "output_filtering"


@dataclass
class SafetyCheckResult:
    """Result of a safety check."""
    check_type: SafetyCheckType
    passed: bool
    risk_level: RiskLevel
    confidence: float  # 0.0 to 1.0
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "check_type": self.check_type.value,
            "passed": self.passed,
            "risk_level": self.risk_level.value,
            "confidence": self.confidence,
            "message": self.message,
            "details": self.details,
            "timestamp": self.timestamp.isoformat()
        }


@dataclass
class SafetyAssessment:
    """Overall safety assessment for a query or action."""
    overall_risk: RiskLevel
    passed_all_checks: bool
    check_results: List[SafetyCheckResult]
    recommendations: List[str]
    blocked: bool
    block_reason: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "overall_risk": self.overall_risk.value,
            "passed_all_checks": self.passed_all_checks,
            "check_results": [result.to_dict() for result in self.check_results],
            "recommendations": self.recommendations,
            "blocked": self.blocked,
            "block_reason": self.block_reason,
            "timestamp": self.timestamp.isoformat()
        }


class PIIDetector:
    """Detects personally identifiable information in text."""
    
    # Patterns for PII detection
    PII_PATTERNS = {
        "email": r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
        "phone": r'\b(?:\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})\b',
        "ssn": r'\b\d{3}-\d{2}-\d{4}\b',
        "credit_card": r'\b(?:\d{4}[-\s]?){3}\d{4}\b',
        "ip_address": r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b',
        "url": r'https?://(?:[-\w.])+(?:[:\d]+)?(?:/(?:[\w/_.])*(?:\?(?:[\w&=%.])*)?(?:#(?:\w*))?)?',
    }
    
    def __init__(self):
        self.compiled_patterns = {
            pii_type: re.compile(pattern, re.IGNORECASE)
            for pii_type, pattern in self.PII_PATTERNS.items()
        }
    
    def detect_pii(self, text: str) -> List[Dict[str, Any]]:
        """Detect PII in text."""
        detections = []
        
        for pii_type, pattern in self.compiled_patterns.items():
            matches = pattern.finditer(text)
            for match in matches:
                detections.append({
                    "type": pii_type,
                    "value": match.group(),
                    "start": match.start(),
                    "end": match.end(),
                    "confidence": self._get_confidence(pii_type, match.group())
                })
        
        return detections
    
    def _get_confidence(self, pii_type: str, value: str) -> float:
        """Get confidence score for PII detection."""
        base_confidence = {
            "email": 0.9,
            "phone": 0.8,
            "ssn": 0.95,
            "credit_card": 0.9,
            "ip_address": 0.7,
            "url": 0.6
        }
        
        confidence = base_confidence.get(pii_type, 0.5)
        
        # Adjust confidence based on context
        if pii_type == "phone" and len(value.replace("-", "").replace(" ", "").replace("(", "").replace(")", "")) != 10:
            confidence *= 0.5
        elif pii_type == "ssn" and not self._is_valid_ssn(value):
            confidence *= 0.3
        
        return confidence
    
    def _is_valid_ssn(self, ssn: str) -> bool:
        """Basic SSN validation."""
        parts = ssn.split("-")
        if len(parts) != 3:
            return False
        
        area, group, serial = parts
        if len(area) != 3 or len(group) != 2 or len(serial) != 4:
            return False
        
        # Basic validation rules
        if area == "000" or area == "666":
            return False
        if area.startswith("9"):
            return False
        if group == "00" or serial == "0000":
            return False
        
        return True


class SQLInjectionDetector:
    """Detects potential SQL injection attacks."""
    
    # SQL injection patterns
    INJECTION_PATTERNS = [
        r"(\b(UNION|SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|EXECUTE)\b)",
        r"(--|#|/\*|\*/)",
        r"(\bOR\b.*\b1\s*=\s*1\b|\bAND\b.*\b1\s*=\s*1\b)",
        r"(\bOR\b.*\bTRUE\b|\bAND\b.*\bTRUE\b)",
        r"(\;\s*(DROP|DELETE|UPDATE|INSERT)\b)",
        r"(\bWAITFOR\s+DELAY\b)",
        r"(\bBENCHMARK\b\s*\()",
        r"(\bSLEEP\b\s*\()",
        r"(\bPG_SLEEP\b\s*\()",
        r"(\bXP_CMDSHELL\b)",
        r"(\bSP_EXECUTESQL\b)",
    ]
    
    def __init__(self):
        self.compiled_patterns = [
            re.compile(pattern, re.IGNORECASE | re.MULTILINE | re.DOTALL)
            for pattern in self.INJECTION_PATTERNS
        ]
    
    def detect_injection(self, query: str) -> List[Dict[str, Any]]:
        """Detect potential SQL injection in query."""
        detections = []
        
        for i, pattern in enumerate(self.compiled_patterns):
            matches = pattern.finditer(query)
            for match in matches:
                detections.append({
                    "pattern_id": i,
                    "match": match.group(),
                    "start": match.start(),
                    "end": match.end(),
                    "confidence": self._get_injection_confidence(match.group())
                })
        
        return detections
    
    def _get_injection_confidence(self, match: str) -> float:
        """Get confidence score for injection detection."""
        match_lower = match.lower()
        
        # High confidence patterns
        if any(keyword in match_lower for keyword in ["union select", "drop table", "delete from", "insert into"]):
            return 0.95
        elif any(keyword in match_lower for keyword in ["--", "/*", "*/"]):
            return 0.9
        elif "1=1" in match_lower or "true" in match_lower:
            return 0.85
        elif any(keyword in match_lower for keyword in ["waitfor delay", "sleep(", "benchmark("]):
            return 0.9
        elif any(keyword in match_lower for keyword in ["xp_cmdshell", "sp_executesql"]):
            return 0.95
        
        return 0.7


class QueryValidator:
    """Validates SQL queries for safety and complexity."""
    
    def __init__(self, max_complexity_score: int = 100):
        self.max_complexity_score = max_complexity_score
    
    def validate_query(self, query: str, schema_info: Optional[Dict[str, Any]] = None) -> SafetyCheckResult:
        """Validate SQL query."""
        issues = []
        complexity_score = 0
        
        # Check query complexity
        complexity_score = self._calculate_complexity(query)
        if complexity_score > self.max_complexity_score:
            issues.append(f"Query complexity too high: {complexity_score}")
        
        # Check for dangerous operations
        dangerous_operations = self._check_dangerous_operations(query)
        if dangerous_operations:
            issues.extend([f"Dangerous operation detected: {op}" for op in dangerous_operations])
        
        # Check table access if schema is provided
        if schema_info:
            table_issues = self._check_table_access(query, schema_info)
            issues.extend(table_issues)
        
        # Determine risk level
        if complexity_score > self.max_complexity_score * 0.8 or dangerous_operations:
            risk_level = RiskLevel.HIGH
        elif complexity_score > self.max_complexity_score * 0.5:
            risk_level = RiskLevel.MEDIUM
        else:
            risk_level = RiskLevel.LOW
        
        passed = len(issues) == 0
        confidence = 0.9 if passed else max(0.1, 1.0 - (len(issues) * 0.2))
        
        return SafetyCheckResult(
            check_type=SafetyCheckType.QUERY_COMPLEXITY,
            passed=passed,
            risk_level=risk_level,
            confidence=confidence,
            message="Query validation completed" if passed else f"Query validation failed: {'; '.join(issues)}",
            details={
                "complexity_score": complexity_score,
                "max_complexity": self.max_complexity_score,
                "issues": issues,
                "dangerous_operations": dangerous_operations
            }
        )
    
    def _calculate_complexity(self, query: str) -> int:
        """Calculate query complexity score."""
        query_lower = query.lower()
        score = 0
        
        # Base score for query type
        if "select" in query_lower:
            score += 10
        if "join" in query_lower:
            score += 15 * query_lower.count("join")
        if "subquery" in query_lower or "(" in query:
            score += 10 * query.count("(")
        if "union" in query_lower:
            score += 20 * query_lower.count("union")
        if "group by" in query_lower:
            score += 10
        if "order by" in query_lower:
            score += 5
        if "having" in query_lower:
            score += 10
        if "case" in query_lower:
            score += 5 * query_lower.count("case")
        if "window" in query_lower or "over(" in query_lower:
            score += 15
        
        # Length-based complexity
        score += min(len(query) // 100, 20)
        
        return score
    
    def _check_dangerous_operations(self, query: str) -> List[str]:
        """Check for dangerous SQL operations."""
        query_lower = query.lower()
        dangerous = []
        
        dangerous_keywords = [
            "drop", "truncate", "delete", "update", "insert", 
            "alter", "create", "exec", "execute"
        ]
        
        for keyword in dangerous_keywords:
            if keyword in query_lower:
                dangerous.append(keyword)
        
        return dangerous
    
    def _check_table_access(self, query: str, schema_info: Dict[str, Any]) -> List[str]:
        """Check if query accesses sensitive tables."""
        issues = []
        query_lower = query.lower()
        
        # Define sensitive table patterns
        sensitive_patterns = [
            "user", "password", "credential", "auth", "token",
            "key", "secret", "private", "confidential"
        ]
        
        tables = schema_info.get("tables", [])
        for table in tables:
            table_name = table.get("name", "").lower()
            if table_name in query_lower:
                for pattern in sensitive_patterns:
                    if pattern in table_name:
                        issues.append(f"Access to sensitive table: {table_name}")
                        break
        
        return issues


class SafetyManager:
    """Main safety manager for AskDB agent."""
    
    def __init__(self, settings=None):
        self.settings = settings or get_settings()
        self.pii_detector = PIIDetector()
        self.injection_detector = SQLInjectionDetector()
        self.query_validator = QueryValidator(
            max_complexity_score=self.settings.max_query_complexity
        )
        
        # Sensitive tables and columns (using defaults as these aren't in Settings yet)
        self.sensitive_tables = set()
        self.sensitive_columns = set()
        
        # Risk thresholds (using defaults as these aren't in Settings yet)
        self.risk_thresholds = {
            RiskLevel.LOW: True,
            RiskLevel.MEDIUM: True,
            RiskLevel.HIGH: False,
            RiskLevel.CRITICAL: False
        }
        
        self.logger = logging.getLogger(__name__)
    
    def assess_query_safety(self, query: str, context: Optional[Dict[str, Any]] = None) -> SafetyAssessment:
        """Assess the safety of a query."""
        check_results = []
        
        # PII detection
        pii_result = self._check_pii(query)
        check_results.append(pii_result)
        
        # SQL injection detection
        injection_result = self._check_sql_injection(query)
        check_results.append(injection_result)
        
        # Query validation
        schema_info = context.get("schema_info") if context else None
        validation_result = self.query_validator.validate_query(query, schema_info)
        check_results.append(validation_result)
        
        # Data access check
        data_access_result = self._check_data_access(query, context)
        check_results.append(data_access_result)
        
        # Overall assessment
        overall_assessment = self._create_overall_assessment(check_results)
        
        self.logger.info(f"Safety assessment completed for query: {overall_assessment.overall_risk.value}")
        
        return overall_assessment
    
    def assess_output_safety(self, output: str, query: str) -> SafetyCheckResult:
        """Assess the safety of query output."""
        # Check for PII in output
        pii_detections = self.pii_detector.detect_pii(output)
        
        if pii_detections:
            return SafetyCheckResult(
                check_type=SafetyCheckType.OUTPUT_FILTERING,
                passed=False,
                risk_level=RiskLevel.HIGH,
                confidence=0.9,
                message=f"PII detected in output: {len(pii_detections)} instances",
                details={
                    "pii_detections": pii_detections,
                    "filtered_output": self._filter_pii(output)
                }
            )
        
        return SafetyCheckResult(
            check_type=SafetyCheckType.OUTPUT_FILTERING,
            passed=True,
            risk_level=RiskLevel.LOW,
            confidence=0.95,
            message="Output safety check passed",
            details={"pii_detections": []}
        )
    
    def _check_pii(self, text: str) -> SafetyCheckResult:
        """Check for PII in text."""
        detections = self.pii_detector.detect_pii(text)
        
        if detections:
            max_confidence = max(d["confidence"] for d in detections)
            risk_level = RiskLevel.HIGH if max_confidence > 0.8 else RiskLevel.MEDIUM
            
            return SafetyCheckResult(
                check_type=SafetyCheckType.PII_DETECTION,
                passed=False,
                risk_level=risk_level,
                confidence=max_confidence,
                message=f"PII detected: {len(detections)} instances",
                details={"detections": detections}
            )
        
        return SafetyCheckResult(
            check_type=SafetyCheckType.PII_DETECTION,
            passed=True,
            risk_level=RiskLevel.LOW,
            confidence=0.9,
            message="No PII detected",
            details={"detections": []}
        )
    
    def _check_sql_injection(self, query: str) -> SafetyCheckResult:
        """Check for SQL injection."""
        detections = self.injection_detector.detect_injection(query)
        
        if detections:
            max_confidence = max(d["confidence"] for d in detections)
            risk_level = RiskLevel.CRITICAL if max_confidence > 0.9 else RiskLevel.HIGH
            
            return SafetyCheckResult(
                check_type=SafetyCheckType.SQL_INJECTION,
                passed=False,
                risk_level=risk_level,
                confidence=max_confidence,
                message=f"Potential SQL injection detected: {len(detections)} patterns",
                details={"detections": detections}
            )
        
        return SafetyCheckResult(
            check_type=SafetyCheckType.SQL_INJECTION,
            passed=True,
            risk_level=RiskLevel.LOW,
            confidence=0.85,
            message="No SQL injection patterns detected",
            details={"detections": []}
        )
    
    def _check_data_access(self, query: str, context: Optional[Dict[str, Any]] = None) -> SafetyCheckResult:
        """Check data access patterns."""
        query_lower = query.lower()
        issues = []
        
        # Check for sensitive table access
        for table in self.sensitive_tables:
            if table.lower() in query_lower:
                issues.append(f"Access to sensitive table: {table}")
        
        # Check for sensitive column access
        for column in self.sensitive_columns:
            if column.lower() in query_lower:
                issues.append(f"Access to sensitive column: {column}")
        
        # Check for data aggregation patterns that might be risky
        risky_patterns = ["count(*)", "sum(", "avg(", "max(", "min("]
        for pattern in risky_patterns:
            if pattern in query_lower:
                issues.append(f"Data aggregation pattern: {pattern}")
        
        if issues:
            return SafetyCheckResult(
                check_type=SafetyCheckType.DATA_ACCESS,
                passed=False,
                risk_level=RiskLevel.MEDIUM,
                confidence=0.8,
                message=f"Data access concerns: {'; '.join(issues)}",
                details={"issues": issues}
            )
        
        return SafetyCheckResult(
            check_type=SafetyCheckType.DATA_ACCESS,
            passed=True,
            risk_level=RiskLevel.LOW,
            confidence=0.9,
            message="Data access check passed",
            details={"issues": []}
        )
    
    def _create_overall_assessment(self, check_results: List[SafetyCheckResult]) -> SafetyAssessment:
        """Create overall safety assessment."""
        # Determine if all checks passed
        passed_all = all(result.passed for result in check_results)
        
        # Determine overall risk level (highest risk among failed checks)
        failed_checks = [r for r in check_results if not r.passed]
        if failed_checks:
            overall_risk = max(failed_checks, key=lambda x: x.risk_level.value).risk_level
        else:
            overall_risk = RiskLevel.LOW
        
        # Generate recommendations
        recommendations = self._generate_recommendations(check_results)
        
        # Determine if should be blocked
        blocked = not self.risk_thresholds.get(overall_risk, False)
        block_reason = None
        if blocked:
            block_reason = f"Query blocked due to {overall_risk.value} risk level"
        
        return SafetyAssessment(
            overall_risk=overall_risk,
            passed_all_checks=passed_all,
            check_results=check_results,
            recommendations=recommendations,
            blocked=blocked,
            block_reason=block_reason
        )
    
    def _generate_recommendations(self, check_results: List[SafetyCheckResult]) -> List[str]:
        """Generate safety recommendations based on check results."""
        recommendations = []
        
        for result in check_results:
            if not result.passed:
                if result.check_type == SafetyCheckType.PII_DETECTION:
                    recommendations.append("Remove or mask personally identifiable information from the query")
                elif result.check_type == SafetyCheckType.SQL_INJECTION:
                    recommendations.append("Review query for potential SQL injection patterns")
                elif result.check_type == SafetyCheckType.QUERY_COMPLEXITY:
                    recommendations.append("Simplify the query or break it into smaller parts")
                elif result.check_type == SafetyCheckType.DATA_ACCESS:
                    recommendations.append("Review data access patterns and consider less sensitive alternatives")
        
        return recommendations
    
    def _filter_pii(self, text: str) -> str:
        """Filter PII from text."""
        filtered_text = text
        detections = self.pii_detector.detect_pii(text)
        
        # Sort detections by position (reverse order to avoid index shifting)
        detections.sort(key=lambda x: x["start"], reverse=True)
        
        for detection in detections:
            start, end = detection["start"], detection["end"]
            filtered_text = filtered_text[:start] + "[REDACTED]" + filtered_text[end:]
        
        return filtered_text
    
    def is_safe_to_execute(self, assessment: SafetyAssessment) -> bool:
        """Check if it's safe to execute based on assessment."""
        return not assessment.blocked and assessment.passed_all_checks
    
    def get_safe_output(self, output: str, assessment: SafetyAssessment) -> str:
        """Get safe output based on assessment."""
        # Check if output filtering is needed
        output_check = next(
            (r for r in assessment.check_results if r.check_type == SafetyCheckType.OUTPUT_FILTERING),
            None
        )
        
        if output_check and not output_check.passed:
            return output_check.details.get("filtered_output", output)
        
        return output


# Global safety manager instance
_safety_manager = None


def get_safety_manager(settings=None) -> SafetyManager:
    """Get the global safety manager instance."""
    global _safety_manager
    if _safety_manager is None:
        _safety_manager = SafetyManager(settings)
    return _safety_manager


def create_safety_manager(settings=None) -> SafetyManager:
    """Create a new safety manager instance."""
    return SafetyManager(settings)


def assess_query_safety(query: str, context: Optional[Dict[str, Any]] = None) -> SafetyAssessment:
    """Convenience function for query safety assessment."""
    manager = get_safety_manager()
    return manager.assess_query_safety(query, context)


def assess_output_safety(output: str, query: str) -> SafetyCheckResult:
    """Convenience function for output safety assessment."""
    manager = get_safety_manager()
    return manager.assess_output_safety(output, query)