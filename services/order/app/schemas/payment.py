from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, validator
from datetime import datetime

class PaymentCreateRequest(BaseModel):
    """Payment creation request."""
    order_id: str = Field(..., description="The ID of the order")
    amount: float = Field(..., gt=0, description="The payment amount")
    payment_method: str = Field(..., description="The payment method")
    payment_method_id: Optional[str] = Field(None, description="The Stripe payment method ID")
    use_stripe: Optional[bool] = Field(True, description="Whether to use Stripe for payment processing")
    currency: Optional[str] = Field("usd", description="The currency for the payment")

class PaymentProcessRequest(BaseModel):
    """Payment process request."""
    payment_intent_id: str = Field(..., description="The payment intent ID")
    success: bool = Field(True, description="Whether the payment was successful")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata for the payment")
    payment_method_id: Optional[str] = Field(None, description="The Stripe payment method ID")

class PaymentResponse(BaseModel):
    """Payment response model."""
    payment_intent_id: str
    order_id: str
    amount: float
    payment_method: Optional[str] = None
    status: str
    created_at: str
    updated_at: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    client_secret: Optional[str] = None
    currency: Optional[str] = "usd"

class CustomerCreateRequest(BaseModel):
    """Customer creation request for payment profiles."""
    email: str = Field(..., description="The customer's email address")
    name: Optional[str] = Field(None, description="The customer's name")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")

class PaymentMethodCreateRequest(BaseModel):
    """Payment method creation request."""
    payment_method_id: str = Field(..., description="The Stripe payment method ID")
    set_as_default: Optional[bool] = Field(False, description="Whether to set as default payment method")

class PaymentMethodResponse(BaseModel):
    """Payment method response model."""
    id: str
    payment_method_id: str
    type: str
    last4: Optional[str] = None
    exp_month: Optional[int] = None
    exp_year: Optional[int] = None
    brand: Optional[str] = None
    is_default: bool
    created_at: str

class CustomerProfileResponse(BaseModel):
    """Customer payment profile response model."""
    user_id: str
    stripe_customer_id: Optional[str] = None
    email: str
    name: Optional[str] = None
    created_at: str
    updated_at: Optional[str] = None
    payment_methods: List[PaymentMethodResponse] = []

class PaymentHistoryResponse(BaseModel):
    """Payment history response model."""
    payments: List[PaymentResponse]
    total_count: int