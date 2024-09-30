import typing
import httpx
import os
from urllib.parse import urlparse, parse_qs
import urllib.parse
from urllib.parse import urlencode
import json
from starlette.responses import Response, JSONResponse
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware
from nc_py_api import NextcloudApp
from nc_py_api.ex_app import AppAPIAuthMiddleware, LogLvl, run_app, nc_app
from nc_py_api.ex_app.integration_fastapi import fetch_models_task


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


APP = FastAPI(lifespan=lifespan)
APP.add_middleware(AppAPIAuthMiddleware)
APP.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)


def enabled_handler(enabled: bool, nc: NextcloudApp) -> str:
    print(f"{nc.app_cfg.app_name}={enabled}")
    if enabled:
        nc.log(LogLvl.INFO, f"{nc.app_cfg.app_name} is enabled")
    else:
        nc.log(LogLvl.INFO, f"{nc.app_cfg.app_name} is disabled")
    return ""


@APP.get("/heartbeat")
async def heartbeat_callback():
    return JSONResponse(content={"status": "ok"})


@APP.post("/init")
async def init_callback(
    b_tasks: BackgroundTasks, nc: typing.Annotated[NextcloudApp, Depends(nc_app)]
):
    b_tasks.add_task(fetch_models_task, nc, {}, 0)
    return JSONResponse(content={})


@APP.put("/enabled")
async def enabled_callback(
    enabled: bool, nc: typing.Annotated[NextcloudApp, Depends(nc_app)]
):
    return JSONResponse(content={"error": enabled_handler(enabled, nc)})


@APP.api_route(
    "/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "HEAD", "PATCH", "OPTIONS"]
)
async def proxy_Requests(_request: Request, path: str):
    response = await proxy_request_to_server(_request, path)

    headers = dict(response.headers)
    headers.pop("transfer-encoding", None)
    headers.pop("content-encoding", None)
    headers["content-length"] = str(response.content.__len__())
    headers["content-security-policy"] = (
        "default-src * 'unsafe-inline' 'unsafe-eval' data: blob:;"
    )

    return Response(
        content=response.content,
        status_code=response.status_code,
        headers=headers,
    )


async def proxy_request_to_server(request: Request, path: str):
    async with httpx.AsyncClient(follow_redirects=False) as client:
        backend_url = get_backend_url()
        url = f"{backend_url}/{path}"
        headers = {}
        for k, v in request.headers.items():
            # NOTE:
            # - remove 'host' to make op routes work
            # - remove 'origin' to validate csrf
            if k == "host" or k == "origin":
                continue
            headers[k] = v

        if request.method == "GET":
            params=request.query_params
            # A referrer header is required when we request to '/work_packages/menu' enpoint
            # Currently the browser does not provide the referer header so it has been put through proxy
            # Also it works even referrer is empty
            if url.endswith("/work_packages/menu"):
                headers.update({'referer': ''})

            if "/project_storages/new" in url :
                # when requesting the storate_id is stripped in the proxy (issue: https://github.com/cloud-py-api/app_api/issues/384). 
                # This piece of code modifies the query param to add missing storage_id.
                query_params = dict(params)
                if 'storages_project_storage[]' in query_params:
                    value = query_params['storages_project_storage[]']
                    new_key = 'storages_project_storage[storage_id]'
                    query_params[new_key] = value
                    del query_params['storages_project_storage[]']
                params = urlencode(query_params, doseq=True)
            response = await client.get(
                url,
                params=params,
                headers=headers,
            )
        else:
            response = await client.request(
                method=request.method,
                url=url,
                params=request.query_params,
                headers=headers,
                content=await request.body(),
            )
        

        if response.is_redirect and not response.status_code == 304:
            if "location" in response.headers and "proxy/openproject-nextcloud-app" in response.headers["location"]:
                redirect_path = urlparse(response.headers["location"]).path
                redirect_url = get_nc_url() + redirect_path
                response.headers["location"] = redirect_url
                response.status_code = 200
            elif "oauth/authorize" in url:
                return response
            elif "apps/oauth2/authorize" in response.headers["location"]:
                response.status_code = 200
                return response
            else:
                headers["content-length"] = "0"
                response = await handle_redirects(
                    client,
                    request.method if response.status_code == 307 else "GET",
                    response.headers["location"],
                    headers,
                )
        return response


async def handle_redirects(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    headers: dict,
):
    response = await client.request(
        method=method,
        url=url,
        headers=headers,
    )

    if response.is_redirect:
        return await handle_redirects(
            client,
            method if response.status_code == 307 else "GET",
            response.headers["location"],
            headers,
        )

    return response


def get_backend_url():
    return os.getenv("OP_BACKEND_URL", "http://localhost:3000")


def get_nc_url():
    nc_url = os.getenv("NEXTCLOUD_URL", "http://localhost/index.php")
    url = urlparse(nc_url)
    return f"{url.scheme}://{url.netloc}"


if __name__ == "__main__":
    run_app("main:APP", log_level="trace")