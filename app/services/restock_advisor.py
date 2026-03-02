"""
智能补货建议引擎
基于销售趋势、库存周转率、供应商交期自动生成补货建议
"""
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from app.models.product import Product
from app.models.inventory import Inventory
from app.models.order import Order, OrderItem
from app.models.supplier import Supplier
from app.schemas.restock import RestockRecommendation, RestockPriority


class RestockAdvisor:
    """智能补货顾问"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def analyze_product(
        self,
        product_id: int,
        days_history: int = 30,
        safety_stock_days: int = 7
    ) -> Optional[RestockRecommendation]:
        """
        分析单个产品的补货需求
        
        Args:
            product_id: 产品ID
            days_history: 历史销售天数
            safety_stock_days: 安全库存天数
        """
        product = self.db.query(Product).filter(Product.id == product_id).first()
        if not product:
            return None
        
        # 获取库存信息
        inventory = self.db.query(Inventory).filter(
            Inventory.product_id == product_id
        ).first()
        
        if not inventory:
            return None
        
        current_stock = inventory.available_quantity
        
        # 计算日均销量
        start_date = datetime.utcnow() - timedelta(days=days_history)
        sales_data = self.db.query(
            func.sum(OrderItem.quantity).label('total_sold')
        ).join(Order).filter(
            and_(
                OrderItem.product_id == product_id,
                Order.created_at >= start_date,
                Order.status.in_(['confirmed', 'shipped', 'delivered'])
            )
        ).first()
        
        total_sold = sales_data.total_sold or 0
        daily_sales_rate = total_sold / days_history if days_history > 0 else 0
        
        # 获取供应商交期
        supplier = self.db.query(Supplier).filter(
            Supplier.id == product.supplier_id
        ).first()
        lead_time_days = supplier.lead_time_days if supplier else 14
        
        # 计算补货参数
        safety_stock = daily_sales_rate * safety_stock_days
        reorder_point = (daily_sales_rate * lead_time_days) + safety_stock
        
        # 经济订货量 (EOQ) - 简化版
        # EOQ = sqrt(2 * D * S / H)
        # D = 年需求量, S = 订货成本, H = 持有成本
        annual_demand = daily_sales_rate * 365
        order_cost = 100  # 假设订货成本
        holding_cost = product.cost * 0.2  # 假设持有成本为成本的20%
        
        if holding_cost > 0:
            eoq = ((2 * annual_demand * order_cost) / holding_cost) ** 0.5
        else:
            eoq = daily_sales_rate * 30  # 默认30天库存
        
        # 判断是否需要补货
        needs_restock = current_stock <= reorder_point
        
        # 计算建议订货量
        if needs_restock:
            suggested_quantity = max(eoq, reorder_point - current_stock)
        else:
            suggested_quantity = 0
        
        # 计算库存可用天数
        days_of_stock = current_stock / daily_sales_rate if daily_sales_rate > 0 else 999
        
        # 确定优先级
        if days_of_stock <= safety_stock_days:
            priority = RestockPriority.URGENT
        elif days_of_stock <= lead_time_days:
            priority = RestockPriority.HIGH
        elif needs_restock:
            priority = RestockPriority.MEDIUM
        else:
            priority = RestockPriority.LOW
        
        return RestockRecommendation(
            product_id=product_id,
            product_sku=product.sku,
            product_name=product.name,
            current_stock=current_stock,
            daily_sales_rate=round(daily_sales_rate, 2),
            days_of_stock=round(days_of_stock, 1),
            reorder_point=round(reorder_point),
            safety_stock=round(safety_stock),
            suggested_quantity=round(suggested_quantity),
            eoq=round(eoq),
            lead_time_days=lead_time_days,
            priority=priority,
            needs_restock=needs_restock,
            supplier_id=product.supplier_id,
            estimated_cost=round(suggested_quantity * product.cost, 2)
        )
    
    def get_all_recommendations(
        self,
        priority_filter: Optional[RestockPriority] = None,
        limit: int = 100
    ) -> List[RestockRecommendation]:
        """
        获取所有产品的补货建议
        
        Args:
            priority_filter: 优先级过滤
            limit: 返回数量限制
        """
        products = self.db.query(Product).filter(Product.is_active == True).all()
        
        recommendations = []
        for product in products:
            rec = self.analyze_product(product.id)
            if rec:
                if priority_filter is None or rec.priority == priority_filter:
                    recommendations.append(rec)
        
        # 按优先级和库存天数排序
        priority_order = {
            RestockPriority.URGENT: 0,
            RestockPriority.HIGH: 1,
            RestockPriority.MEDIUM: 2,
            RestockPriority.LOW: 3
        }
        
        recommendations.sort(
            key=lambda x: (priority_order[x.priority], x.days_of_stock)
        )
        
        return recommendations[:limit]
    
    def get_urgent_restocks(self) -> List[RestockRecommendation]:
        """获取紧急补货建议"""
        return self.get_all_recommendations(priority_filter=RestockPriority.URGENT)
    
    def calculate_total_restock_cost(
        self,
        recommendations: List[RestockRecommendation]
    ) -> Dict[str, float]:
        """计算总补货成本"""
        total_cost = sum(rec.estimated_cost for rec in recommendations)
        total_units = sum(rec.suggested_quantity for rec in recommendations)
        
        return {
            "total_cost": round(total_cost, 2),
            "total_units": total_units,
            "product_count": len(recommendations),
            "average_cost_per_product": round(total_cost / len(recommendations), 2) if recommendations else 0
        }
