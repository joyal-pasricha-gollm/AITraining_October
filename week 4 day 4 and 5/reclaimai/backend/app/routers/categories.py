import uuid
from fastapi import APIRouter,HTTPException,Query,status
from sqlalchemy import func,select
from sqlalchemy.exc import IntegrityError
from app.dependencies.auth import AdminUser,CurrentUser,DatabaseSession,OptionalCurrentUser
from app.models.category import Category
from app.models.enums import UserRole
from app.schemas.category import CategoryCreate,CategoryListResponse,CategoryResponse,CategoryUpdate
router=APIRouter(prefix="/api/v1/categories",tags=["Categories"])
@router.get("",response_model=CategoryListResponse)
def list_categories(db:DatabaseSession,user:OptionalCurrentUser,include_inactive:bool=Query(False)):
    if include_inactive and (user is None or user.role!=UserRole.ADMIN): raise HTTPException(403,detail={"code":"FORBIDDEN","message":"Administrator permission is required to view inactive categories."})
    query=select(Category)
    if not include_inactive:query=query.where(Category.is_active.is_(True))
    items=list(db.scalars(query.order_by(Category.name)).all()); return {"items":items,"total":len(items)}
@router.get("/{category_id}",response_model=CategoryResponse)
def get_category(category_id:uuid.UUID,db:DatabaseSession,user:OptionalCurrentUser):
    obj=db.get(Category,category_id)
    if obj is None or (not obj.is_active and (user is None or user.role!=UserRole.ADMIN)):raise HTTPException(404,detail={"code":"NOT_FOUND","message":"Category was not found."})
    return obj
@router.post("",response_model=CategoryResponse,status_code=201)
def create_category(data:CategoryCreate,db:DatabaseSession,admin:AdminUser):
    if db.scalar(select(Category).where(func.lower(Category.name)==data.name.lower())):raise HTTPException(409,detail={"code":"DUPLICATE_RESOURCE","message":"A category with this name already exists."})
    obj=Category(name=data.name,description=data.description);db.add(obj)
    try:db.commit();db.refresh(obj)
    except IntegrityError as e:db.rollback();raise HTTPException(409,detail={"code":"DUPLICATE_RESOURCE","message":"A category with this name already exists."}) from e
    return obj
@router.patch("/{category_id}",response_model=CategoryResponse)
def update_category(category_id:uuid.UUID,data:CategoryUpdate,db:DatabaseSession,admin:AdminUser):
    obj=db.get(Category,category_id)
    if obj is None:raise HTTPException(404,detail={"code":"NOT_FOUND","message":"Category was not found."})
    changes=data.model_dump(exclude_unset=True)
    if not changes:raise HTTPException(422,detail={"code":"VALIDATION_ERROR","message":"At least one category field must be supplied."})
    if "name" in changes and db.scalar(select(Category).where(func.lower(Category.name)==changes["name"].lower(),Category.id!=obj.id)):raise HTTPException(409,detail={"code":"DUPLICATE_RESOURCE","message":"A category with this name already exists."})
    for k,v in changes.items():setattr(obj,k,v)
    try:
        db.commit()
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(409,detail={"code":"DUPLICATE_RESOURCE","message":"A category with this name already exists."}) from e
    db.refresh(obj);return obj
