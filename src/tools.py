"""
工具模块
定义智能客服可使用的工具（模拟数据）
"""
from typing import Dict, List, Any
from langchain.tools import BaseTool
from pydantic import BaseModel, Field


# 模拟订单数据
MOCK_ORDERS = {
    "12345678": {
        "order_id": "12345678",
        "status": "已发货",
        "tracking_number": "SF1234567890",
        "estimated_delivery": "明天",
        "items": ["iPhone 15 Pro", "手机壳"],
        "total": 8999
    },
    "87654321": {
        "order_id": "87654321",
        "status": "待发货",
        "tracking_number": None,
        "estimated_delivery": "3天后",
        "items": ["MacBook Air"],
        "total": 7999
    },
    "11111111": {
        "order_id": "11111111",
        "status": "已送达",
        "tracking_number": "JD9876543210",
        "estimated_delivery": "已送达",
        "items": ["AirPods Pro"],
        "total": 1899
    }
}

# 模拟商品数据
MOCK_PRODUCTS = [
    {
        "id": "p001",
        "name": "iPhone 15 Pro",
        "category": "手机",
        "price": 7999,
        "description": "最新款iPhone，A17芯片，钛金属边框",
        "stock": 100
    },
    {
        "id": "p002",
        "name": "MacBook Air M3",
        "category": "电脑",
        "price": 8999,
        "description": "轻薄笔记本，M3芯片，15小时续航",
        "stock": 50
    },
    {
        "id": "p003",
        "name": "AirPods Pro 2",
        "category": "配件",
        "price": 1899,
        "description": "主动降噪，空间音频，自适应通透模式",
        "stock": 200
    },
    {
        "id": "p004",
        "name": "小米14 Ultra",
        "category": "手机",
        "price": 5999,
        "description": "徕卡影像，骁龙8 Gen3，5000mAh电池",
        "stock": 80
    },
    {
        "id": "p005",
        "name": "华为Mate 60 Pro",
        "category": "手机",
        "price": 6999,
        "description": "麒麟9000S，卫星通信，昆仑玻璃",
        "stock": 60
    }
]


class OrderQueryInput(BaseModel):
    """订单查询输入"""
    order_id: str = Field(description="订单号")


class ProductSearchInput(BaseModel):
    """商品搜索输入"""
    keyword: str = Field(description="搜索关键词或商品类别")
    max_price: int = Field(default=10000, description="最高价格")


class CreateTicketInput(BaseModel):
    """创建工单输入"""
    issue_type: str = Field(description="问题类型")
    description: str = Field(description="问题描述")


class OrderQueryTool(BaseTool):
    """订单查询工具"""
    name: str = "order_query"
    description: str = "查询订单状态和物流信息。输入订单号，返回订单详情。"
    args_schema: type[BaseModel] = OrderQueryInput

    def _run(self, order_id: str) -> str:
        """执行订单查询"""
        order = MOCK_ORDERS.get(order_id)
        if order:
            return f"""订单查询结果：
订单号：{order['order_id']}
状态：{order['status']}
物流单号：{order['tracking_number'] or '暂无'}
预计送达：{order['estimated_delivery']}
商品：{', '.join(order['items'])}
金额：¥{order['total']}"""
        return f"未找到订单号为 {order_id} 的订单，请检查订单号是否正确。"


class ProductSearchTool(BaseTool):
    """商品搜索工具"""
    name: str = "product_search"
    description: str = "搜索商品信息。输入关键词或类别，返回匹配的商品列表。"
    args_schema: type[BaseModel] = ProductSearchInput

    def _run(self, keyword: str, max_price: int = 10000) -> str:
        """执行商品搜索"""
        keyword_lower = keyword.lower()
        results = []

        for product in MOCK_PRODUCTS:
            if product["price"] > max_price:
                continue
            if (keyword_lower in product["name"].lower() or
                keyword_lower in product["category"].lower() or
                keyword_lower in product["description"].lower()):
                results.append(product)

        if not results:
            return f"未找到与 '{keyword}' 相关且价格在 ¥{max_price} 以下的商品。"

        result_text = f"找到 {len(results)} 个相关商品：\n"
        for p in results:
            result_text += f"\n- {p['name']} (¥{p['price']})\n  {p['description']}\n  库存：{p['stock']}件"
        return result_text


class CreateTicketTool(BaseTool):
    """创建工单工具"""
    name: str = "create_ticket"
    description: str = "创建投诉或反馈工单。记录用户的问题和反馈。"
    args_schema: type[BaseModel] = CreateTicketInput

    def _run(self, issue_type: str, description: str) -> str:
        """创建工单"""
        import random
        ticket_id = f"TK{random.randint(100000, 999999)}"
        return f"""工单创建成功！
工单号：{ticket_id}
问题类型：{issue_type}
问题描述：{description}

我们会在24小时内处理您的反馈，处理结果将通过短信通知您。
感谢您的反馈！"""


# 工具实例
def get_tools() -> List[BaseTool]:
    """获取所有可用工具"""
    return [
        OrderQueryTool(),
        ProductSearchTool(),
        CreateTicketTool(),
    ]


# 工具映射（用于快速查找）
TOOL_MAP = {
    "order_query": OrderQueryTool(),
    "product_search": ProductSearchTool(),
    "create_ticket": CreateTicketTool(),
}
