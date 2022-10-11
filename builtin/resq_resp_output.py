#!/user/bin/env python
# -*- coding: utf-8 -*-
import os
import json
import time
import datetime
import requests
from loguru import logger
from enum import Enum
from pydantic import BaseModel, HttpUrl, Field
from typing import Any, Dict, Text, Union, Callable, List, Tuple, Optional

Name = Text
Url = Text
BaseUrl = Union[HttpUrl, Text]
VariablesMapping = Dict[Text, Any]
FunctionsMapping = Dict[Text, Callable]
Headers = Dict[Text, Text]
Cookies = Dict[Text, Text]
Verify = Optional[bool]
checker_item = Union[List, Tuple, Text]


class MethodEnum(Text, Enum):
    """Method"""
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    HEAD = "HEAD"
    OPTIONS = "OPTIONS"
    PATCH = "PATCH"


class RespData(BaseModel):
    """Response.Response Model"""
    status_code: int
    headers: Dict
    cookies: Cookies = {}
    encoding: Union[Text, None] = None
    content_type: Text
    body: Union[Dict, Text, bytes, List]


class ReqData(BaseModel):
    """Response.Request Model"""
    method: MethodEnum = MethodEnum.GET
    url: Url
    headers: Headers = {}
    cookies: Cookies = {}
    body: Union[Text, bytes, Dict, List, None] = {}


class RequestOutput:

    @staticmethod
    def console_output(title, result):
        msg = f"\n================== {title}  details ==================\n"
        for key, value in result.dict().items():
            if isinstance(value, dict):
                value = json.dumps(value, indent=4, ensure_ascii=False)
            msg += "{:<8} : {}\n".format(key, value)
        logger.info(msg)

    @staticmethod
    def analyse_result(title, result):
        result.encoding = "utf-8"
        req = ReqData(
            method=result.request.method,
            url=result.request.url.split("private_token")[0],
            headers=result.request.headers,
            cookies=result.request._cookies,
            body=result.request.body
        )
        RequestOutput.console_output(f"{title} request", req)
        if result.headers["Content-Type"].find("json") != -1:
            try:
                rep_body = result.json()
            except Exception as e:
                logger.warning("Failed to parse data with JSON, switch to text parsing！")
                result.encoding = "utf-8"
                rep_body = result.text
        elif result.headers["Content-Type"].find("xml") != -1 \
                or result.headers["Content-Type"].find("html") != -1 \
                or result.headers["Content-Type"].find("text") != -1:
            result.encoding = "utf-8"
            rep_body = result.text
        else:
            rep_body = result.content
        resp = RespData(
            status_code=result.status_code,
            cookies=result.cookies,
            encoding=result.encoding,
            headers=result.headers,
            content_type=result.headers.get("content-type"),
            body=rep_body
        )
        RequestOutput.console_output(f"{title} response", resp)
