"""补货建议数据模型"""
from enum import Enum
from pydantic import BaseModel, Field
from typing import Optional


class RestockPriority(str, Enum):
    """补货优先级"""
    URGENT = "urgent"      # 紧急：库存不足7天
    HIGH = "high"          # 高：库存不足交期
    MEDIUM = "medium"      # 中：达到补货点
    LOW = "low"            # 低：库存充足


class RestockRecommendation(BaseModel):
    """补货建议"""
    product_id: int
    product_sku: str
    product_name: str
    current_stock: int = Field(..., description="当前库存")
    daily_sales_rate: float = Field(..., description="日均销量")
    days_of_stock: float = Field(..., description="库存可用天数")
    reorder_point: int = Field(..., description="补货点")
    safety_stock: int = Field(..., description="安全库存")
    suggested_quantity: int = Field(..., description="建议订货量")
    eoq: int = Field(..., description="经济订货量")
    lead_time_days: int = Field(..., description="供应商交期(天)")
    priority: RestockPriority
    needs_restock: bool
    supplier_id: Optional[int] = None
    estimated_cost: float = Field(..., description="预估成本")
    
    class Config:
        from_attributes = True


class RestockSummary(BaseModel):
    """补货汇总"""
    total_cost: float
    total_units: int
    product_count: int
    average_cost_per_product: float
    recommendations: list[RestockRecommendation]
