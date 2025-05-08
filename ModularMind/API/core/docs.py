from fastapi import FastAPI
from fastapi.openapi.docs import get_swagger_ui_html, get_redoc_html
from fastapi.openapi.utils import get_openapi
import os

def setup_docs(app: FastAPI) -> None:
    """
    API dokümantasyonu için Swagger ve ReDoc yapılandırması.
    
    Args:
        app: FastAPI uygulaması
    """
    app_name = os.getenv("APP_NAME", "ModularMind API")
    app_version = os.getenv("APP_VERSION", "1.0.0")
    app_description = os.getenv("APP_DESCRIPTION", """
    ModularMind API, Retrieval-Augmented Generation (RAG) sistemi için RESTful API sağlar.
    
    ## Belgeler
    
    * **Doküman yükleme ve yönetim** - Bilgi tabanına dokümanlar ekleyin
    * **Sorgulama** - Dokümanlar üzerinde akıllı sorgular yapın
    * **Kullanıcı yönetimi** - Kullanıcıları ve erişim izinlerini yönetin
    * **Geri bildirim** - Yanıtların kalitesini iyileştirmek için geri bildirim toplama
    
    ## Kimlik Doğrulama
    
    API, Bearer token tabanlı JWT kimlik doğrulaması kullanır. Token almak için `/auth/token` endpoint'ini kullanın.
    """)
    
    # OpenAPI şemasını oluşturmak için özel işlev
    def custom_openapi():
        if app.openapi_schema:
            return app.openapi_schema
        
        openapi_schema = get_openapi(
            title=app_name,
            version=app_version,
            description=app_description,
            routes=app.routes,
        )
        
        # Güvenlik şeması ekleme
        openapi_schema["components"]["securitySchemes"] = {
            "bearerAuth": {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "JWT",
            }
        }
        
        # Global güvenlik gerekliliği ekleme
        openapi_schema["security"] = [{"bearerAuth": []}]
        
        app.openapi_schema = openapi_schema
        return app.openapi_schema
    
    # Özel OpenAPI şemasını ayarla
    app.openapi = custom_openapi
    
    # Swagger UI'ı özelleştirmek için özel route ekleme 
    @app.get("/docs", include_in_schema=False)
    async def custom_swagger_ui_html():
        return get_swagger_ui_html(
            openapi_url=app.openapi_url,
            title=f"{app_name} - Swagger UI",
            oauth2_redirect_url=app.swagger_ui_oauth2_redirect_url,
            swagger_js_url="/static/swagger-ui-bundle.js",
            swagger_css_url="/static/swagger-ui.css",
        )
    
    # ReDoc UI'ı özelleştirmek için özel route ekleme
    @app.get("/redoc", include_in_schema=False)
    async def custom_redoc_html():
        return get_redoc_html(
            openapi_url=app.openapi_url,
            title=f"{app_name} - ReDoc",
            redoc_js_url="/static/redoc.standalone.js",
        )