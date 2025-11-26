"""
Comprehensive test suite for AskDB safety protocols.

This module tests all safety-related functionality including:
- Risk classification and assessment
- PII detection and filtering
- SQL injection detection and prevention
- Query validation and complexity analysis
- Safety manager coordination
- Multi-layered safety protocols
"""

import pytest
import asyncio
import json
import time
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict, Any, List

from askdb.agent.safety import (
    SafetyManager, PIIDetector, SQLInjectionDetector, QueryValidator,
    RiskLevel, SafetyCheckType, SafetyCheckResult, SafetyAssessment,
    get_safety_manager, assess_query_safety, assess_output_safety
)
from askdb.config import get_settings, Settings


class TestSafetyManager:
    """Test cases for SafetyManager class."""
    
    @pytest.fixture
    def safety_manager(self):
        """Create a SafetyManager instance for testing."""
        settings = Settings(
            safety={
                "enable_pii_detection": True,
                "enable_sql_injection_detection": True,
                "enable_query_validation": True,
                "max_query_complexity": 50,
                "risk_thresholds": {
                    "low": 0.3,
                    "medium": 0.6,
                    "high": 0.8
                }
            }
        )
        return SafetyManager(settings=settings)
    
    @pytest.fixture
    def mock_settings(self):
        """Create mock settings for testing."""
        return Mock(spec=Settings)
    
    def test_safety_manager_initialization(self, safety_manager):
        """Test SafetyManager initialization."""
        assert safety_manager.settings is not None
        assert safety_manager.pii_detector is not None
        assert safety_manager.sql_injection_detector is not None
        assert safety_manager.query_validator is not None
    
    def test_safety_manager_initialization_with_default_settings(self):
        """Test SafetyManager initialization with default settings."""
        manager = SafetyManager()
        assert manager.settings is not None
        assert manager.pii_detector is not None
        assert manager.sql_injection_detector is not None
        assert manager.query_validator is not None
    
    def test_assess_query_safety_low_risk(self, safety_manager):
        """Test query safety assessment for low risk query."""
        query = "SELECT name, email FROM users WHERE age > 18"
        context = {"user_intent": "data_retrieval"}
        
        assessment = safety_manager.assess_query_safety(query, context)
        
        assert isinstance(assessment, SafetyAssessment)
        assert assessment.risk_level in [RiskLevel.LOW, RiskLevel.MEDIUM]
        assert assessment.is_safe is True
        assert assessment.query == query
        assert assessment.context == context
        assert len(assessment.check_results) > 0
        assert assessment.timestamp is not None
    
    def test_assess_query_safety_high_risk(self, safety_manager):
        """Test query safety assessment for high risk query."""
        query = "DROP TABLE users; --"
        context = {"user_intent": "unknown"}
        
        assessment = safety_manager.assess_query_safety(query, context)
        
        assert isinstance(assessment, SafetyAssessment)
        assert assessment.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]
        assert assessment.is_safe is False
        assert any(check.check_type == SafetyCheckType.SQL_INJECTION 
                  for check in assessment.check_results)
    
    def test_assess_query_safety_with_pii(self, safety_manager):
        """Test query safety assessment with PII detection."""
        query = "SELECT * FROM users WHERE email = 'john@example.com'"
        context = {"user_intent": "data_retrieval"}
        
        assessment = safety_manager.assess_query_safety(query, context)
        
        assert isinstance(assessment, SafetyAssessment)
        # Should detect PII in the query
        pii_checks = [check for check in assessment.check_results 
                     if check.check_type == SafetyCheckType.PII_DETECTION]
        assert len(pii_checks) > 0
    
    def test_assess_output_safety_safe(self, safety_manager):
        """Test output safety assessment for safe output."""
        output = "Query executed successfully. Found 5 users."
        query = "SELECT COUNT(*) FROM users"
        
        result = safety_manager.assess_output_safety(output, query)
        
        assert isinstance(result, SafetyCheckResult)
        assert result.is_safe is True
        assert result.risk_score < 0.5
        assert result.check_type == SafetyCheckType.OUTPUT_FILTERING
    
    def test_assess_output_safety_with_pii(self, safety_manager):
        """Test output safety assessment with PII in output."""
        output = "User: John Doe, Email: john@example.com, Phone: 555-1234"
        query = "SELECT * FROM users WHERE id = 1"
        
        result = safety_manager.assess_output_safety(output, query)
        
        assert isinstance(result, SafetyCheckResult)
        assert result.is_safe is False  # Should detect PII
        assert result.risk_score > 0.5
        assert "PII" in result.reason
    
    def test_is_safe_to_execute(self, safety_manager):
        """Test is_safe_to_execute method."""
        # Safe query
        safe_query = "SELECT name FROM users"
        assert safety_manager.is_safe_to_execute(safe_query) is True
        
        # Unsafe query
        unsafe_query = "DROP TABLE users"
        assert safety_manager.is_safe_to_execute(unsafe_query) is False
    
    def test_get_safe_output(self, safety_manager):
        """Test get_safe_output method."""
        # Safe output
        safe_output = "Found 10 records"
        query = "SELECT COUNT(*) FROM users"
        filtered_output = safety_manager.get_safe_output(safe_output, query)
        assert filtered_output == safe_output
        
        # Output with PII
        pii_output = "User: John Doe, Email: john@example.com"
        filtered_output = safety_manager.get_safe_output(pii_output, query)
        assert "john@example.com" not in filtered_output
        assert "[PII_FILTERED]" in filtered_output or "REDACTED" in filtered_output
    
    def test_safety_assessment_serialization(self, safety_manager):
        """Test SafetyAssessment serialization."""
        query = "SELECT * FROM users"
        context = {"test": "context"}
        
        assessment = safety_manager.assess_query_safety(query, context)
        assessment_dict = assessment.to_dict()
        
        assert isinstance(assessment_dict, dict)
        assert "risk_level" in assessment_dict
        assert "risk_score" in assessment_dict
        assert "is_safe" in assessment_dict
        assert "query" in assessment_dict
        assert "context" in assessment_dict
        assert "check_results" in assessment_dict
        assert "timestamp" in assessment_dict
        
        # Test reconstruction
        reconstructed = SafetyAssessment.from_dict(assessment_dict)
        assert reconstructed.risk_level == assessment.risk_level
        assert reconstructed.risk_score == assessment.risk_score
        assert reconstructed.is_safe == assessment.is_safe


class TestPIIDetector:
    """Test cases for PIIDetector class."""
    
    @pytest.fixture
    def pii_detector(self):
        """Create a PIIDetector instance for testing."""
        return PIIDetector()
    
    def test_detect_email_addresses(self, pii_detector):
        """Test email address detection."""
        text = "Contact john.doe@example.com for more information"
        pii_data = pii_detector.detect_pii(text)
        
        assert len(pii_data) > 0
        assert any(pii["type"] == "email" for pii in pii_data)
        assert "john.doe@example.com" in pii_data[0]["value"]
    
    def test_detect_phone_numbers(self, pii_detector):
        """Test phone number detection."""
        text = "Call me at 555-123-4567 or (555) 987-6543"
        pii_data = pii_detector.detect_pii(text)
        
        assert len(pii_data) > 0
        assert any(pii["type"] == "phone" for pii in pii_data)
    
    def test_detect_social_security_numbers(self, pii_detector):
        """Test SSN detection."""
        text = "My SSN is 123-45-6789"
        pii_data = pii_detector.detect_pii(text)
        
        assert len(pii_data) > 0
        assert any(pii["type"] == "ssn" for pii in pii_data)
    
    def test_detect_credit_card_numbers(self, pii_detector):
        """Test credit card number detection."""
        text = "Card number: 4532-1234-5678-9012"
        pii_data = pii_detector.detect_pii(text)
        
        assert len(pii_data) > 0
        assert any(pii["type"] == "credit_card" for pii in pii_data)
    
    def test_detect_addresses(self, pii_detector):
        """Test address detection."""
        text = "Live at 123 Main St, New York, NY 10001"
        pii_data = pii_detector.detect_pii(text)
        
        assert len(pii_data) > 0
        assert any(pii["type"] == "address" for pii in pii_data)
    
    def test_detect_no_pii(self, pii_detector):
        """Test text with no PII."""
        text = "This is a simple text without personal information"
        pii_data = pii_detector.detect_pii(text)
        
        assert len(pii_data) == 0
    
    def test_detect_multiple_pii_types(self, pii_detector):
        """Test detection of multiple PII types in one text."""
        text = "John Doe (john@example.com, 555-123-4567) lives at 123 Main St"
        pii_data = pii_detector.detect_pii(text)
        
        assert len(pii_data) >= 3
        pii_types = {pii["type"] for pii in pii_data}
        assert "email" in pii_types
        assert "phone" in pii_types
        assert "address" in pii_types
    
    def test_pii_data_structure(self, pii_detector):
        """Test PII data structure."""
        text = "Email: test@example.com"
        pii_data = pii_detector.detect_pii(text)
        
        assert len(pii_data) > 0
        pii = pii_data[0]
        assert "type" in pii
        assert "value" in pii
        assert "start" in pii
        assert "end" in pii
        assert "confidence" in pii
        assert isinstance(pii["confidence"], float)
        assert 0 <= pii["confidence"] <= 1


class TestSQLInjectionDetector:
    """Test cases for SQLInjectionDetector class."""
    
    @pytest.fixture
    def injection_detector(self):
        """Create a SQLInjectionDetector instance for testing."""
        return SQLInjectionDetector()
    
    def test_detect_union_based_injection(self, injection_detector):
        """Test UNION-based SQL injection detection."""
        query = "SELECT name FROM users WHERE id = 1 UNION SELECT password FROM admin"
        result = injection_detector.detect_injection(query)
        
        assert result.detected is True
        assert result.risk_score > 0.7
        assert "UNION" in result.reason.upper()
    
    def test_detect_comment_based_injection(self, injection_detector):
        """Test comment-based SQL injection detection."""
        query = "SELECT * FROM users WHERE id = 1; DROP TABLE users; --"
        result = injection_detector.detect_injection(query)
        
        assert result.detected is True
        assert result.risk_score > 0.8
        assert "DROP" in result.reason.upper()
    
    def test_detect_tautology_based_injection(self, injection_detector):
        """Test tautology-based SQL injection detection."""
        query = "SELECT * FROM users WHERE username = 'admin' OR '1'='1'"
        result = injection_detector.detect_injection(query)
        
        assert result.detected is True
        assert result.risk_score > 0.6
    
    def test_detect_stored_procedure_injection(self, injection_detector):
        """Test stored procedure SQL injection detection."""
        query = "EXEC sp_configure 'show advanced options', 1"
        result = injection_detector.detect_injection(query)
        
        assert result.detected is True
        assert result.risk_score > 0.7
    
    def test_detect_time_based_injection(self, injection_detector):
        """Test time-based SQL injection detection."""
        query = "SELECT * FROM users WHERE id = 1; WAITFOR DELAY '00:00:05'"
        result = injection_detector.detect_injection(query)
        
        assert result.detected is True
        assert result.risk_score > 0.6
    
    def test_detect_no_injection(self, injection_detector):
        """Test safe SQL query."""
        query = "SELECT name, email FROM users WHERE age > 18 AND status = 'active'"
        result = injection_detector.detect_injection(query)
        
        assert result.detected is False
        assert result.risk_score < 0.3
    
    def test_detect_blind_sql_injection(self, injection_detector):
        """Test blind SQL injection detection."""
        query = "SELECT * FROM users WHERE id = 1 AND (SELECT COUNT(*) FROM admin) > 0"
        result = injection_detector.detect_injection(query)
        
        assert result.detected is True
        assert result.risk_score > 0.5
    
    def test_detect_second_order_injection(self, injection_detector):
        """Test second-order SQL injection detection."""
        query = "INSERT INTO logs (message) VALUES ('User input'); DROP TABLE users; --"
        result = injection_detector.detect_injection(query)
        
        assert result.detected is True
        assert result.risk_score > 0.8
    
    def test_injection_result_structure(self, injection_detector):
        """Test injection detection result structure."""
        query = "SELECT * FROM users WHERE id = 1; DROP TABLE users;"
        result = injection_detector.detect_injection(query)
        
        assert hasattr(result, 'detected')
        assert hasattr(result, 'risk_score')
        assert hasattr(result, 'reason')
        assert hasattr(result, 'patterns_found')
        assert isinstance(result.detected, bool)
        assert isinstance(result.risk_score, float)
        assert isinstance(result.reason, str)
        assert isinstance(result.patterns_found, list)


class TestQueryValidator:
    """Test cases for QueryValidator class."""
    
    @pytest.fixture
    def query_validator(self):
        """Create a QueryValidator instance for testing."""
        return QueryValidator(max_complexity_score=100)
    
    def test_validate_simple_select(self, query_validator):
        """Test validation of simple SELECT query."""
        query = "SELECT name, email FROM users"
        result = query_validator.validate_query(query)
        
        assert result.is_valid is True
        assert result.complexity_score < 20
        assert result.estimated_execution_time < 1.0
    
    def test_validate_complex_join(self, query_validator):
        """Test validation of complex JOIN query."""
        query = """
        SELECT u.name, o.total, p.product_name
        FROM users u
        JOIN orders o ON u.id = o.user_id
        JOIN order_items oi ON o.id = oi.order_id
        JOIN products p ON oi.product_id = p.id
        WHERE u.created_at > '2023-01-01'
        GROUP BY u.id, o.id
        HAVING COUNT(o.id) > 5
        ORDER BY o.total DESC
        LIMIT 100
        """
        result = query_validator.validate_query(query)
        
        assert result.is_valid is True
        assert result.complexity_score > 30
        assert "JOIN" in result.complexity_factors
    
    def test_validate_subquery(self, query_validator):
        """Test validation of subquery."""
        query = """
        SELECT name FROM users 
        WHERE id IN (
            SELECT user_id FROM orders 
            WHERE total > (SELECT AVG(total) FROM orders)
        )
        """
        result = query_validator.validate_query(query)
        
        assert result.is_valid is True
        assert "SUBQUERY" in result.complexity_factors
    
    def test_validate_aggregate_query(self, query_validator):
        """Test validation of aggregate query."""
        query = """
        SELECT department, COUNT(*) as count, AVG(salary) as avg_salary
        FROM employees
        GROUP BY department
        HAVING COUNT(*) > 10
        """
        result = query_validator.validate_query(query)
        
        assert result.is_valid is True
        assert "AGGREGATE" in result.complexity_factors
    
    def test_validate_too_complex_query(self, query_validator):
        """Test validation of overly complex query."""
        # Create a very complex query
        query = "SELECT * FROM users u1 " + \
                "JOIN users u2 ON u1.id = u2.id " * 20 + \
                "WHERE u1.id IN (SELECT id FROM users " + \
                "JOIN users ON id = id " * 20 + ")"
        
        result = query_validator.validate_query(query)
        
        assert result.is_valid is False
        assert result.complexity_score > query_validator.max_complexity_score
        assert "TOO_COMPLEX" in result.reason
    
    def test_validate_invalid_sql(self, query_validator):
        """Test validation of invalid SQL syntax."""
        query = "SELCT name FORM users"  # Intentional typo
        result = query_validator.validate_query(query)
        
        assert result.is_valid is False
        assert "SYNTAX_ERROR" in result.reason
    
    def test_validate_empty_query(self, query_validator):
        """Test validation of empty query."""
        result = query_validator.validate_query("")
        
        assert result.is_valid is False
        assert "EMPTY" in result.reason
    
    def test_validate_query_with_risky_operations(self, query_validator):
        """Test validation of query with risky operations."""
        query = "DELETE FROM users WHERE created_at < '2020-01-01'"
        result = query_validator.validate_query(query)
        
        # Should be valid but with high complexity due to DELETE
        assert result.is_valid is True
        assert "DELETE" in result.complexity_factors
        assert result.complexity_score > 20
    
    def test_calculate_query_complexity(self, query_validator):
        """Test query complexity calculation."""
        # Simple query
        simple_query = "SELECT * FROM users"
        simple_score = query_validator._calculate_complexity(simple_query)
        assert simple_score < 10
        
        # Complex query
        complex_query = """
        SELECT u.name, COUNT(o.id) as order_count
        FROM users u
        JOIN orders o ON u.id = o.user_id
        WHERE u.created_at > '2023-01-01'
        GROUP BY u.id
        HAVING COUNT(o.id) > 5
        ORDER BY order_count DESC
        """
        complex_score = query_validator._calculate_complexity(complex_query)
        assert complex_score > simple_score
        assert complex_score > 20


class TestSafetyIntegration:
    """Test cases for safety system integration."""
    
    @pytest.fixture
    def integrated_safety_manager(self):
        """Create SafetyManager with all components."""
        settings = Settings(
            safety={
                "enable_pii_detection": True,
                "enable_sql_injection_detection": True,
                "enable_query_validation": True,
                "max_query_complexity": 50,
                "risk_thresholds": {
                    "low": 0.3,
                    "medium": 0.6,
                    "high": 0.8
                }
            }
        )
        return SafetyManager(settings=settings)
    
    def test_comprehensive_safety_assessment(self, integrated_safety_manager):
        """Test comprehensive safety assessment with all checks."""
        # Query with multiple safety issues
        query = "SELECT * FROM users WHERE email = 'john@example.com'; DROP TABLE users; --"
        context = {"user_intent": "data_modification"}
        
        assessment = integrated_safety_manager.assess_query_safety(query, context)
        
        assert isinstance(assessment, SafetyAssessment)
        assert assessment.is_safe is False
        assert assessment.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]
        
        # Should have multiple check results
        check_types = {check.check_type for check in assessment.check_results}
        assert SafetyCheckType.SQL_INJECTION in check_types
        assert SafetyCheckType.PII_DETECTION in check_types
        assert SafetyCheckType.QUERY_VALIDATION in check_types
    
    def test_safety_manager_with_disabled_components(self):
        """Test SafetyManager with disabled components."""
        settings = Settings(
            safety={
                "enable_pii_detection": False,
                "enable_sql_injection_detection": False,
                "enable_query_validation": True,
                "max_query_complexity": 50
            }
        )
        manager = SafetyManager(settings=settings)
        
        query = "SELECT email FROM users WHERE email = 'test@example.com'"
        assessment = manager.assess_query_safety(query)
        
        # Should only have query validation check
        check_types = {check.check_type for check in assessment.check_results}
        assert SafetyCheckType.QUERY_VALIDATION in check_types
        assert SafetyCheckType.PII_DETECTION not in check_types
        assert SafetyCheckType.SQL_INJECTION not in check_types
    
    def test_concurrent_safety_assessments(self, integrated_safety_manager):
        """Test concurrent safety assessments."""
        queries = [
            "SELECT * FROM users",
            "SELECT email FROM users WHERE id = 1",
            "DROP TABLE users",
            "SELECT name FROM users WHERE email = 'test@example.com'"
        ]
        
        async def assess_query(query):
            return integrated_safety_manager.assess_query_safety(query)
        
        # Run assessments concurrently
        tasks = [assess_query(query) for query in queries]
        results = asyncio.run(asyncio.gather(*tasks))
        
        assert len(results) == len(queries)
        for result in results:
            assert isinstance(result, SafetyAssessment)
    
    def test_safety_performance(self, integrated_safety_manager):
        """Test safety assessment performance."""
        query = "SELECT name, email FROM users WHERE age > 18"
        
        start_time = time.time()
        assessment = integrated_safety_manager.assess_query_safety(query)
        end_time = time.time()
        
        execution_time = end_time - start_time
        assert execution_time < 1.0  # Should complete within 1 second
        assert isinstance(assessment, SafetyAssessment)


class TestSafetyUtilities:
    """Test cases for safety utility functions."""
    
    def test_get_safety_manager(self):
        """Test get_safety_manager utility function."""
        manager = get_safety_manager()
        assert isinstance(manager, SafetyManager)
    
    def test_assess_query_safety_utility(self):
        """Test assess_query_safety utility function."""
        query = "SELECT * FROM users"
        assessment = assess_query_safety(query)
        
        assert isinstance(assessment, SafetyAssessment)
        assert assessment.query == query
    
    def test_assess_output_safety_utility(self):
        """Test assess_output_safety utility function."""
        output = "Query executed successfully"
        query = "SELECT COUNT(*) FROM users"
        result = assess_output_safety(output, query)
        
        assert isinstance(result, SafetyCheckResult)
        assert result.check_type == SafetyCheckType.OUTPUT_FILTERING
    
    def test_risk_level_comparison(self):
        """Test RiskLevel comparison operations."""
        assert RiskLevel.LOW < RiskLevel.MEDIUM
        assert RiskLevel.MEDIUM < RiskLevel.HIGH
        assert RiskLevel.HIGH < RiskLevel.CRITICAL
        assert RiskLevel.LOW != RiskLevel.HIGH
    
    def test_safety_check_result_creation(self):
        """Test SafetyCheckResult creation and validation."""
        result = SafetyCheckResult(
            check_type=SafetyCheckType.SQL_INJECTION,
            is_safe=False,
            risk_score=0.8,
            reason="Potential SQL injection detected",
            details={"pattern": "DROP TABLE"}
        )
        
        assert result.check_type == SafetyCheckType.SQL_INJECTION
        assert result.is_safe is False
        assert result.risk_score == 0.8
        assert "SQL injection" in result.reason
        assert result.details["pattern"] == "DROP TABLE"


class TestSafetyEdgeCases:
    """Test edge cases and error handling in safety system."""
    
    @pytest.fixture
    def safety_manager(self):
        """Create SafetyManager for edge case testing."""
        return SafetyManager()
    
    def test_empty_query_assessment(self, safety_manager):
        """Test safety assessment with empty query."""
        assessment = safety_manager.assess_query_safety("")
        
        assert isinstance(assessment, SafetyAssessment)
        assert assessment.risk_level == RiskLevel.HIGH
        assert assessment.is_safe is False
    
    def test_none_query_assessment(self, safety_manager):
        """Test safety assessment with None query."""
        with pytest.raises((TypeError, ValueError)):
            safety_manager.assess_query_safety(None)
    
    def test_very_long_query_assessment(self, safety_manager):
        """Test safety assessment with very long query."""
        long_query = "SELECT * FROM users WHERE " + "name = 'test' OR " * 1000 + "1=1"
        assessment = safety_manager.assess_query_safety(long_query)
        
        assert isinstance(assessment, SafetyAssessment)
        # Should handle long queries without crashing
    
    def test_unicode_characters_in_query(self, safety_manager):
        """Test safety assessment with Unicode characters."""
        unicode_query = "SELECT * FROM users WHERE name = 'José García' AND email = 'test@exemple.com'"
        assessment = safety_manager.assess_query_safety(unicode_query)
        
        assert isinstance(assessment, SafetyAssessment)
        # Should handle Unicode without issues
    
    def test_malformed_json_context(self, safety_manager):
        """Test safety assessment with malformed context."""
        query = "SELECT * FROM users"
        context = {"malformed": object()}  # Non-serializable object
        
        # Should handle gracefully
        assessment = safety_manager.assess_query_safety(query, context)
        assert isinstance(assessment, SafetyAssessment)
    
    def test_empty_output_assessment(self, safety_manager):
        """Test output safety assessment with empty output."""
        result = safety_manager.assess_output_safety("", "SELECT * FROM users")
        
        assert isinstance(result, SafetyCheckResult)
        assert result.is_safe is True
    
    def test_none_output_assessment(self, safety_manager):
        """Test output safety assessment with None output."""
        result = safety_manager.assess_output_safety(None, "SELECT * FROM users")
        
        assert isinstance(result, SafetyCheckResult)
        assert result.is_safe is True


# Performance and stress tests
class TestSafetyPerformance:
    """Performance tests for safety system."""
    
    @pytest.fixture
    def safety_manager(self):
        """Create SafetyManager for performance testing."""
        return SafetyManager()
    
    def test_bulk_query_assessment_performance(self, safety_manager):
        """Test performance of bulk query assessments."""
        queries = [
            "SELECT * FROM users WHERE id = {}".format(i)
            for i in range(100)
        ]
        
        start_time = time.time()
        assessments = [safety_manager.assess_query_safety(query) for query in queries]
        end_time = time.time()
        
        total_time = end_time - start_time
        avg_time = total_time / len(queries)
        
        assert len(assessments) == len(queries)
        assert avg_time < 0.1  # Average should be less than 100ms per query
        assert total_time < 10.0  # Total should be less than 10 seconds
    
    def test_memory_usage_stability(self, safety_manager):
        """Test memory usage stability during repeated assessments."""
        import gc
        import sys
        
        query = "SELECT * FROM users WHERE name = 'test'"
        
        # Force garbage collection before test
        gc.collect()
        initial_objects = len(gc.get_objects())
        
        # Run many assessments
        for _ in range(1000):
            assessment = safety_manager.assess_query_safety(query)
            del assessment
        
        # Force garbage collection after test
        gc.collect()
        final_objects = len(gc.get_objects())
        
        # Memory usage should be relatively stable
        object_increase = final_objects - initial_objects
        assert object_increase < 1000  # Allow some increase but not excessive


# Integration tests with real-world scenarios
class TestSafetyRealWorldScenarios:
    """Test safety system with real-world scenarios."""
    
    @pytest.fixture
    def safety_manager(self):
        """Create SafetyManager for real-world testing."""
        return SafetyManager()
    
    def test_business_intelligence_query(self, safety_manager):
        """Test safety assessment for typical BI query."""
        query = """
        SELECT 
            c.customer_name,
            COUNT(o.order_id) as total_orders,
            SUM(o.order_total) as total_spent,
            AVG(o.order_total) as avg_order_value
        FROM customers c
        JOIN orders o ON c.customer_id = o.customer_id
        WHERE o.order_date >= '2023-01-01'
            AND o.order_date < '2024-01-01'
        GROUP BY c.customer_id, c.customer_name
        HAVING COUNT(o.order_id) > 10
        ORDER BY total_spent DESC
        LIMIT 100
        """
        
        assessment = safety_manager.assess_query_safety(query)
        
        assert isinstance(assessment, SafetyAssessment)
        assert assessment.is_safe is True
        assert assessment.risk_level in [RiskLevel.LOW, RiskLevel.MEDIUM]
    
    def test_admin_maintenance_query(self, safety_manager):
        """Test safety assessment for admin maintenance query."""
        query = """
        UPDATE users 
        SET last_login = NOW(), status = 'inactive'
        WHERE last_login < '2023-01-01' 
            AND status = 'active'
        """
        
        assessment = safety_manager.assess_query_safety(query)
        
        assert isinstance(assessment, SafetyAssessment)
        # UPDATE queries should have medium risk
        assert assessment.risk_level in [RiskLevel.MEDIUM, RiskLevel.HIGH]
    
    def test_data_export_query(self, safety_manager):
        """Test safety assessment for data export query."""
        query = """
        SELECT 
            user_id,
            email,
            first_name,
            last_name,
            phone,
            address,
            created_at
        FROM users
        WHERE created_at >= '2023-01-01'
        ORDER BY created_at DESC
        """
        
        assessment = safety_manager.assess_query_safety(query)
        
        assert isinstance(assessment, SafetyAssessment)
        # Should detect potential PII exposure
        pii_checks = [check for check in assessment.check_results 
                     if check.check_type == SafetyCheckType.PII_DETECTION]
        assert len(pii_checks) > 0
    
    def test_analytics_aggregation_query(self, safety_manager):
        """Test safety assessment for analytics aggregation query."""
        query = """
        SELECT 
            DATE_TRUNC('month', order_date) as month,
            product_category,
            COUNT(DISTINCT customer_id) as unique_customers,
            COUNT(order_id) as total_orders,
            SUM(order_total) as revenue,
            AVG(order_total) as avg_order_value
        FROM orders o
        JOIN products p ON o.product_id = p.product_id
        WHERE order_date >= '2023-01-01'
        GROUP BY DATE_TRUNC('month', order_date), product_category
        ORDER BY month, revenue DESC
        """
        
        assessment = safety_manager.assess_query_safety(query)
        
        assert isinstance(assessment, SafetyAssessment)
        assert assessment.is_safe is True
        # Complex but safe query
        assert assessment.risk_level in [RiskLevel.LOW, RiskLevel.MEDIUM]


if __name__ == "__main__":
    # Run tests when this file is executed directly
    pytest.main([__file__, "-v", "--tb=short"])