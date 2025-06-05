from fastapi import FastAPI, APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional
import uuid
from datetime import datetime, timedelta
import bcrypt
import jwt
from enum import Enum

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# JWT Configuration
SECRET_KEY = "your-secret-key-here"  # In production, use environment variable
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

security = HTTPBearer()

# Enums
class UserRole(str, Enum):
    ADMIN = "admin"
    USER = "user"

# Models
class User(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    username: str
    email: str
    role: UserRole
    created_at: datetime = Field(default_factory=datetime.utcnow)

class UserCreate(BaseModel):
    username: str
    email: str
    password: str
    role: UserRole = UserRole.USER

class UserLogin(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str
    user: User

class Vendor(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    address: str
    phone: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

class VendorCreate(BaseModel):
    name: str
    address: str
    phone: str

class Customer(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    address: str
    phone: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

class CustomerCreate(BaseModel):
    name: str
    address: str
    phone: str

class Product(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    vendor_id: str
    quantity: int
    purchase_price: float
    selling_price: float
    created_at: datetime = Field(default_factory=datetime.utcnow)

class ProductCreate(BaseModel):
    name: str
    vendor_id: str
    quantity: int
    purchase_price: float
    selling_price: float

class SaleItem(BaseModel):
    product_id: str
    product_name: str
    quantity: int
    selling_price: float
    total_amount: float

class Sale(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    customer_id: str
    customer_name: str
    items: List[SaleItem]
    total_amount: float
    created_at: datetime = Field(default_factory=datetime.utcnow)

class SaleCreate(BaseModel):
    customer_id: str
    items: List[SaleItem]

class CompanyDetails(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    address: str
    phone: Optional[str] = None
    email: Optional[str] = None
    tax_number: Optional[str] = None
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class CompanyDetailsUpdate(BaseModel):
    name: str
    address: str
    phone: Optional[str] = None
    email: Optional[str] = None
    tax_number: Optional[str] = None

# Utility functions
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        token = credentials.credentials
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid authentication credentials")
        
        user_data = await db.users.find_one({"username": username})
        if user_data is None:
            raise HTTPException(status_code=401, detail="User not found")
        
        return User(**user_data)
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

async def require_admin(current_user: User = Depends(get_current_user)):
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user

# Routes
@api_router.get("/")
async def root():
    return {"message": "Dashboard API"}

# Authentication routes
@api_router.post("/auth/register", response_model=User)
async def register(user_data: UserCreate):
    # Check if user exists
    existing_user = await db.users.find_one({"$or": [{"username": user_data.username}, {"email": user_data.email}]})
    if existing_user:
        raise HTTPException(status_code=400, detail="Username or email already exists")
    
    # Hash password and create user
    hashed_password = hash_password(user_data.password)
    user_dict = user_data.dict(exclude={"password"})
    user_obj = User(**user_dict)
    
    # Save user with hashed password
    user_doc = user_obj.dict()
    user_doc["password"] = hashed_password
    await db.users.insert_one(user_doc)
    
    return user_obj

@api_router.post("/auth/login", response_model=Token)
async def login(login_data: UserLogin):
    user_data = await db.users.find_one({"username": login_data.username})
    if not user_data or not verify_password(login_data.password, user_data["password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    user = User(**{k: v for k, v in user_data.items() if k != "password"})
    access_token = create_access_token(data={"sub": user.username})
    
    return Token(access_token=access_token, token_type="bearer", user=user)

@api_router.get("/auth/me", response_model=User)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    return current_user

# Vendor routes
@api_router.post("/vendors", response_model=Vendor)
async def create_vendor(vendor_data: VendorCreate, current_user: User = Depends(get_current_user)):
    vendor = Vendor(**vendor_data.dict())
    await db.vendors.insert_one(vendor.dict())
    return vendor

@api_router.get("/vendors", response_model=List[Vendor])
async def get_vendors(current_user: User = Depends(get_current_user)):
    vendors = await db.vendors.find().to_list(1000)
    return [Vendor(**vendor) for vendor in vendors]

@api_router.put("/vendors/{vendor_id}", response_model=Vendor)
async def update_vendor(vendor_id: str, vendor_data: VendorCreate, current_user: User = Depends(get_current_user)):
    updated_vendor = vendor_data.dict()
    updated_vendor["id"] = vendor_id
    vendor = Vendor(**updated_vendor)
    
    result = await db.vendors.replace_one({"id": vendor_id}, vendor.dict())
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Vendor not found")
    return vendor

@api_router.delete("/vendors/{vendor_id}")
async def delete_vendor(vendor_id: str, current_user: User = Depends(require_admin)):
    result = await db.vendors.delete_one({"id": vendor_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Vendor not found")
    return {"message": "Vendor deleted successfully"}

# Customer routes
@api_router.post("/customers", response_model=Customer)
async def create_customer(customer_data: CustomerCreate, current_user: User = Depends(get_current_user)):
    customer = Customer(**customer_data.dict())
    await db.customers.insert_one(customer.dict())
    return customer

@api_router.get("/customers", response_model=List[Customer])
async def get_customers(current_user: User = Depends(get_current_user)):
    customers = await db.customers.find().to_list(1000)
    return [Customer(**customer) for customer in customers]

@api_router.put("/customers/{customer_id}", response_model=Customer)
async def update_customer(customer_id: str, customer_data: CustomerCreate, current_user: User = Depends(get_current_user)):
    updated_customer = customer_data.dict()
    updated_customer["id"] = customer_id
    customer = Customer(**updated_customer)
    
    result = await db.customers.replace_one({"id": customer_id}, customer.dict())
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Customer not found")
    return customer

@api_router.delete("/customers/{customer_id}")
async def delete_customer(customer_id: str, current_user: User = Depends(require_admin)):
    result = await db.customers.delete_one({"id": customer_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Customer not found")
    return {"message": "Customer deleted successfully"}

# Product routes
@api_router.post("/products", response_model=Product)
async def create_product(product_data: ProductCreate, current_user: User = Depends(get_current_user)):
    # Verify vendor exists
    vendor = await db.vendors.find_one({"id": product_data.vendor_id})
    if not vendor:
        raise HTTPException(status_code=400, detail="Vendor not found")
    
    product = Product(**product_data.dict())
    await db.products.insert_one(product.dict())
    return product

@api_router.get("/products", response_model=List[Product])
async def get_products(current_user: User = Depends(get_current_user)):
    products = await db.products.find().to_list(1000)
    return [Product(**product) for product in products]

@api_router.put("/products/{product_id}", response_model=Product)
async def update_product(product_id: str, product_data: ProductCreate, current_user: User = Depends(get_current_user)):
    # Verify vendor exists
    vendor = await db.vendors.find_one({"id": product_data.vendor_id})
    if not vendor:
        raise HTTPException(status_code=400, detail="Vendor not found")
    
    updated_product = product_data.dict()
    updated_product["id"] = product_id
    product = Product(**updated_product)
    
    result = await db.products.replace_one({"id": product_id}, product.dict())
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Product not found")
    return product

@api_router.delete("/products/{product_id}")
async def delete_product(product_id: str, current_user: User = Depends(require_admin)):
    result = await db.products.delete_one({"id": product_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Product not found")
    return {"message": "Product deleted successfully"}

# Sales routes
@api_router.post("/sales", response_model=Sale)
async def create_sale(sale_data: SaleCreate, current_user: User = Depends(get_current_user)):
    # Verify customer exists
    customer = await db.customers.find_one({"id": sale_data.customer_id})
    if not customer:
        raise HTTPException(status_code=400, detail="Customer not found")
    
    # Calculate total and update stock
    total_amount = 0
    for item in sale_data.items:
        # Verify product exists and has enough stock
        product = await db.products.find_one({"id": item.product_id})
        if not product:
            raise HTTPException(status_code=400, detail=f"Product {item.product_id} not found")
        
        if product["quantity"] < item.quantity:
            raise HTTPException(status_code=400, detail=f"Insufficient stock for product {product['name']}")
        
        # Update product stock
        new_quantity = product["quantity"] - item.quantity
        await db.products.update_one(
            {"id": item.product_id},
            {"$set": {"quantity": new_quantity}}
        )
        
        total_amount += item.total_amount
    
    sale = Sale(
        customer_id=sale_data.customer_id,
        customer_name=customer["name"],
        items=sale_data.items,
        total_amount=total_amount
    )
    
    await db.sales.insert_one(sale.dict())
    return sale

@api_router.get("/sales", response_model=List[Sale])
async def get_sales(current_user: User = Depends(get_current_user)):
    sales = await db.sales.find().sort("created_at", -1).to_list(1000)
    return [Sale(**sale) for sale in sales]

# Stock routes
@api_router.get("/stock")
async def get_stock(current_user: User = Depends(get_current_user)):
    products = await db.products.find().to_list(1000)
    stock_data = []
    total_stock_value = 0
    
    for product in products:
        stock_value = product["quantity"] * product["purchase_price"]
        total_stock_value += stock_value
        
        stock_data.append({
            "product_id": product["id"],
            "product_name": product["name"],
            "quantity": product["quantity"],
            "purchase_price": product["purchase_price"],
            "selling_price": product["selling_price"],
            "stock_value": stock_value
        })
    
    return {
        "products": stock_data,
        "total_stock_value": total_stock_value
    }

# Dashboard routes
@api_router.get("/dashboard/stats")
async def get_dashboard_stats(current_user: User = Depends(get_current_user)):
    # Get basic counts
    vendors_count = await db.vendors.count_documents({})
    customers_count = await db.customers.count_documents({})
    products_count = await db.products.count_documents({})
    
    # Get sales data
    sales = await db.sales.find().to_list(1000)
    total_sales = sum(sale["total_amount"] for sale in sales)
    
    # Get stock value
    products = await db.products.find().to_list(1000)
    total_stock_value = sum(product["quantity"] * product["purchase_price"] for product in products)
    total_purchase_value = sum(product["quantity"] * product["purchase_price"] for product in products)
    
    # Monthly sales (last 12 months)
    monthly_sales = {}
    for sale in sales:
        month_key = sale["created_at"].strftime("%Y-%m")
        monthly_sales[month_key] = monthly_sales.get(month_key, 0) + sale["total_amount"]
    
    return {
        "vendors_count": vendors_count,
        "customers_count": customers_count,
        "products_count": products_count,
        "total_sales": total_sales,
        "total_purchase_value": total_purchase_value,
        "total_stock_value": total_stock_value,
        "monthly_sales": monthly_sales
    }

# Company details routes
@api_router.get("/company")
async def get_company_details(current_user: User = Depends(get_current_user)):
    company = await db.company.find_one({})
    if not company:
        # Return default company details
        default_company = CompanyDetails(
            name="ABC Pvt Ltd",
            address="Singur, Hooghly"
        )
        await db.company.insert_one(default_company.dict())
        return default_company
    return CompanyDetails(**company)

@api_router.put("/company", response_model=CompanyDetails)
async def update_company_details(company_data: CompanyDetailsUpdate, current_user: User = Depends(require_admin)):
    existing = await db.company.find_one({})
    
    if existing:
        company = CompanyDetails(**company_data.dict(), id=existing["id"])
        await db.company.replace_one({"id": existing["id"]}, company.dict())
    else:
        company = CompanyDetails(**company_data.dict())
        await db.company.insert_one(company.dict())
    
    return company

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
