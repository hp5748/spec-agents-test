"""
结果验证器模块
验证技能执行结果的质量和格式
"""
import logging
import re
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Callable

from .base import SkillResult, ValidationResult

logger = logging.getLogger(__name__)


@dataclass
class ValidationSchema:
    """验证模式定义"""
    name: str
    description: str = ""
    required_fields: List[str] = field(default_factory=list)
    field_types: Dict[str, type] = field(default_factory=dict)
    field_patterns: Dict[str, str] = field(default_factory=dict)  # 正则表达式
    min_response_length: int = 10
    max_response_length: int = 10000


# 预定义的验证模式
BUILTIN_SCHEMAS: Dict[str, ValidationSchema] = {
    "order_result": ValidationSchema(
        name="order_result",
        description="订单查询结果验证",
        required_fields=["order_id", "status"],
        field_types={
            "order_id": str,
            "status": str
        },
        field_patterns={
            "order_id": r"^[A-Z0-9]{8,15}$"
        }
    ),
    "logistics_result": ValidationSchema(
        name="logistics_result",
        description="物流查询结果验证",
        required_fields=["tracking_number", "status"],
        field_types={
            "tracking_number": str,
            "status": str
        }
    ),
    "product_result": ValidationSchema(
        name="product_result",
        description="商品推荐结果验证",
        required_fields=[],
        min_response_length=20
    ),
    "complaint_result": ValidationSchema(
        name="complaint_result",
        description="投诉处理结果验证",
        required_fields=[],
        min_response_length=30
    ),
    "default": ValidationSchema(
        name="default",
        description="默认验证模式",
        required_fields=[],
        min_response_length=10
    )
}


class ResultValidator:
    """
    结果验证器

    验证技能执行结果是否符合预期格式和质量要求
    """

    def __init__(self, custom_schemas: Dict[str, ValidationSchema] = None):
        """
        初始化验证器

        Args:
            custom_schemas: 自定义验证模式
        """
        self._schemas = BUILTIN_SCHEMAS.copy()
        if custom_schemas:
            self._schemas.update(custom_schemas)

        # 自定义验证器
        self._custom_validators: Dict[str, Callable] = {}

    def register_schema(self, schema: ValidationSchema) -> None:
        """注册验证模式"""
        self._schemas[schema.name] = schema

    def register_validator(self, name: str, validator: Callable) -> None:
        """注册自定义验证函数"""
        self._custom_validators[name] = validator

    def validate(
        self,
        result: SkillResult,
        schema_name: str = "default",
        context: Dict[str, Any] = None
    ) -> ValidationResult:
        """
        验证执行结果

        Args:
            result: 技能执行结果
            schema_name: 验证模式名称
            context: 验证上下文

        Returns:
            验证结果
        """
        errors = []
        warnings = []

        # 获取验证模式
        schema = self._schemas.get(schema_name, self._schemas["default"])

        # 1. 基本状态验证
        if not result.success:
            errors.append(f"执行失败: {result.error}")
            return ValidationResult(
                is_valid=False,
                errors=errors,
                warnings=warnings,
                score=0.0
            )

        # 2. 响应内容验证
        response_valid, response_errors = self._validate_response(result, schema)
        errors.extend(response_errors)

        # 3. 数据字段验证
        if result.data:
            data_valid, data_errors, data_warnings = self._validate_data(result.data, schema)
            errors.extend(data_errors)
            warnings.extend(data_warnings)

        # 4. 自定义验证器
        if schema_name in self._custom_validators:
            try:
                custom_result = self._custom_validators[schema_name](result, context)
                if isinstance(custom_result, tuple):
                    custom_valid, custom_errors = custom_result
                    if not custom_valid:
                        errors.extend(custom_errors)
            except Exception as e:
                warnings.append(f"自定义验证器执行失败: {e}")

        # 计算质量评分
        score = self._calculate_score(result, errors, warnings)

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            score=score
        )

    def _validate_response(
        self,
        result: SkillResult,
        schema: ValidationSchema
    ) -> tuple[bool, List[str]]:
        """验证响应内容"""
        errors = []

        # 检查响应是否为空
        if not result.response or not result.response.strip():
            errors.append("响应内容为空")
            return False, errors

        response = result.response.strip()

        # 检查响应长度
        if len(response) < schema.min_response_length:
            errors.append(f"响应内容过短（{len(response)} < {schema.min_response_length}）")

        if len(response) > schema.max_response_length:
            errors.append(f"响应内容过长（{len(response)} > {schema.max_response_length}）")

        return len(errors) == 0, errors

    def _validate_data(
        self,
        data: Dict[str, Any],
        schema: ValidationSchema
    ) -> tuple[bool, List[str], List[str]]:
        """验证数据字段"""
        errors = []
        warnings = []

        # 检查必需字段
        for field_name in schema.required_fields:
            if field_name not in data:
                errors.append(f"缺少必需字段: {field_name}")
            elif data[field_name] is None:
                errors.append(f"必需字段为空: {field_name}")

        # 检查字段类型
        for field_name, expected_type in schema.field_types.items():
            if field_name in data and data[field_name] is not None:
                if not isinstance(data[field_name], expected_type):
                    actual_type = type(data[field_name]).__name__
                    errors.append(
                        f"字段类型错误: {field_name} "
                        f"(期望 {expected_type.__name__}, 实际 {actual_type})"
                    )

        # 检查字段格式（正则）
        for field_name, pattern in schema.field_patterns.items():
            if field_name in data and data[field_name] is not None:
                value = str(data[field_name])
                if not re.match(pattern, value):
                    errors.append(f"字段格式错误: {field_name} (不匹配模式 {pattern})")

        return len(errors) == 0, errors, warnings

    def _calculate_score(
        self,
        result: SkillResult,
        errors: List[str],
        warnings: List[str]
    ) -> float:
        """计算质量评分"""
        if errors:
            return 0.0

        base_score = 1.0

        # 每个警告扣 0.1 分
        base_score -= len(warnings) * 0.1

        # 响应质量加分
        if result.response:
            # 响应长度适中
            if 50 <= len(result.response) <= 500:
                base_score += 0.1
            # 包含有用数据
            if result.data:
                base_score += 0.1

        return max(0.0, min(1.0, base_score))

    def validate_format(self, result: SkillResult) -> ValidationResult:
        """
        验证结果格式

        简化的格式验证，只检查基本格式
        """
        errors = []

        if not isinstance(result, SkillResult):
            errors.append("结果类型错误")
            return ValidationResult(is_valid=False, errors=errors)

        if not isinstance(result.response, str):
            errors.append("响应必须是字符串")

        if not isinstance(result.data, dict):
            errors.append("数据必须是字典")

        if not isinstance(result.used_tools, list):
            errors.append("使用的工具必须是列表")

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors
        )

    def validate_content(
        self,
        result: SkillResult,
        required_fields: List[str] = None
    ) -> ValidationResult:
        """
        验证内容完整性

        Args:
            result: 技能执行结果
            required_fields: 必需的数据字段

        Returns:
            验证结果
        """
        errors = []
        warnings = []

        # 检查响应内容
        if not result.response or len(result.response.strip()) < 10:
            errors.append("响应内容不足")

        # 检查必需字段
        if required_fields:
            for field in required_fields:
                if field not in result.data:
                    errors.append(f"缺少数据字段: {field}")

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )


# 全局验证器实例
result_validator = ResultValidator()


def validate_result(
    result: SkillResult,
    schema_name: str = "default",
    context: Dict[str, Any] = None
) -> ValidationResult:
    """
    便捷函数：验证技能执行结果

    Args:
        result: 技能执行结果
        schema_name: 验证模式名称
        context: 验证上下文

    Returns:
        验证结果
    """
    return result_validator.validate(result, schema_name, context)
