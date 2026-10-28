from typing import Annotated

from fastapi import APIRouter, File, Query, Request, UploadFile, status
from fastapi.responses import Response
from starlette.concurrency import run_in_threadpool

from app.api.deps import DbDep, SettingsDep, Tenant
from app.api.schemas import ImportSummaryOut, OkOut, Page, ProductOut, VariantOut
from app.api.serializers import product_out
from app.application.dto import ProductCreateCommand, ProductUpdateCommand, VariantInput, VariantUpdate
from app.application.products import ProductService
from app.domain.enums import ProductStatus
from app.domain.errors import ValidationError

router = APIRouter(prefix="/api/products", tags=["products"])


def _service(request: Request, db, ctx) -> ProductService:
    return ProductService(db, ctx, request.app.state.storage)


@router.get("", response_model=Page[ProductOut])
def list_products(
    request: Request, ctx: Tenant, db: DbDep, settings: SettingsDep,
    q: Annotated[str | None, Query(max_length=100)] = None,
    status_filter: Annotated[ProductStatus | None, Query(alias="status")] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
):
    items, total = _service(request, db, ctx).search(
        q=q, status=status_filter.value if status_filter else None, page=page, page_size=page_size)
    return Page(items=[product_out(p, settings.media_url_prefix) for p in items], total=total, page=page,
                page_size=page_size)


@router.post("", response_model=ProductOut, status_code=status.HTTP_201_CREATED)
def create_product(cmd: ProductCreateCommand, request: Request, ctx: Tenant, db: DbDep, settings: SettingsDep):
    return product_out(_service(request, db, ctx).create(cmd), settings.media_url_prefix)


@router.get("/export.csv")
def export_products(request: Request, ctx: Tenant, db: DbDep):
    csv_text = _service(request, db, ctx).export_csv()
    return Response(content=csv_text, media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": 'attachment; filename="products.csv"'})


@router.post("/import", response_model=ImportSummaryOut)
async def import_products(request: Request, ctx: Tenant, db: DbDep, settings: SettingsDep,
                          file: Annotated[UploadFile, File()]):
    data = await file.read(settings.max_csv_bytes + 1)
    if len(data) > settings.max_csv_bytes:
        raise ValidationError("CSV file is too large.")
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValidationError("CSV must be UTF-8 encoded.") from exc
    return await run_in_threadpool(_service(request, db, ctx).import_csv, text)


@router.get("/{product_id}", response_model=ProductOut)
def get_product(product_id: int, request: Request, ctx: Tenant, db: DbDep, settings: SettingsDep):
    return product_out(_service(request, db, ctx).get(product_id), settings.media_url_prefix)


@router.patch("/{product_id}", response_model=ProductOut)
def update_product(product_id: int, cmd: ProductUpdateCommand, request: Request, ctx: Tenant, db: DbDep,
                   settings: SettingsDep):
    return product_out(_service(request, db, ctx).update(product_id, cmd), settings.media_url_prefix)


@router.post("/{product_id}/archive", response_model=ProductOut)
def archive_product(product_id: int, request: Request, ctx: Tenant, db: DbDep, settings: SettingsDep):
    return product_out(_service(request, db, ctx).set_status(product_id, ProductStatus.ARCHIVED),
                       settings.media_url_prefix)


@router.post("/{product_id}/unarchive", response_model=ProductOut)
def unarchive_product(product_id: int, request: Request, ctx: Tenant, db: DbDep, settings: SettingsDep):
    return product_out(_service(request, db, ctx).set_status(product_id, ProductStatus.ACTIVE),
                       settings.media_url_prefix)


@router.post("/{product_id}/image", response_model=ProductOut)
async def upload_image(product_id: int, request: Request, ctx: Tenant, db: DbDep, settings: SettingsDep,
                       file: Annotated[UploadFile, File()]):
    data = await file.read(settings.max_image_bytes + 1)
    product = await run_in_threadpool(_service(request, db, ctx).upload_image, product_id, data,
                                      settings.max_image_bytes)
    return product_out(product, settings.media_url_prefix)


@router.post("/{product_id}/variants", response_model=VariantOut, status_code=status.HTTP_201_CREATED)
def add_variant(product_id: int, cmd: VariantInput, request: Request, ctx: Tenant, db: DbDep):
    return _service(request, db, ctx).add_variant(product_id, cmd)


@router.patch("/{product_id}/variants/{variant_id}", response_model=VariantOut)
def update_variant(product_id: int, variant_id: int, cmd: VariantUpdate, request: Request, ctx: Tenant, db: DbDep):
    return _service(request, db, ctx).update_variant(product_id, variant_id, cmd)


@router.delete("/{product_id}/variants/{variant_id}", response_model=OkOut)
def delete_variant(product_id: int, variant_id: int, request: Request, ctx: Tenant, db: DbDep):
    _service(request, db, ctx).delete_variant(product_id, variant_id)
    return OkOut()
