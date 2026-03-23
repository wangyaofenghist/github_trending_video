"""
快手可灵 AI (Kling) 视频生成服务
文档：https://open.kuaishou.com/open/openDocument?source=kl
"""
import requests
import time
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class KlingAIClient:
    """快手可灵 AI 客户端"""

    def __init__(self, app_key: str, app_secret: str):
        """
        初始化可灵 AI 客户端

        Args:
            app_key: 快手开放平台 AppKey
            app_secret: 快手开放平台 AppSecret
        """
        self.app_key = app_key
        self.app_secret = app_secret
        self.base_url = "https://api.open.kuaishou.com/openapi/kling"
        self.access_token = None
        self.token_expires_at = 0

    def _get_access_token(self) -> Optional[str]:
        """获取访问令牌"""
        if self.access_token and time.time() < self.token_expires_at:
            return self.access_token

        try:
            url = "https://api.open.kuaishou.com/oauth2/access_token"
            params = {
                "appKey": self.app_key,
                "appSecret": self.app_secret,
                "grantType": "client_credentials"
            }

            response = requests.post(url, params=params, timeout=30)
            result = response.json()

            if result.get("result") == 1:
                self.access_token = result["data"]["accessToken"]
                # token 有效期通常为 24 小时，提前 1 小时刷新
                self.token_expires_at = time.time() + 23 * 3600
                logger.info("获取可灵 AI 访问令牌成功")
                return self.access_token
            else:
                logger.error(f"获取可灵 AI 访问令牌失败：{result}")
                return None

        except Exception as e:
            logger.error(f"获取可灵 AI 访问令牌异常：{e}")
            return None

    def text_to_video(
        self,
        prompt: str,
        model: str = "kling-v1",
        duration: int = 5,
        resolution: str = "720p",
        aspect_ratio: str = "16:9"
    ) -> Dict[str, Any]:
        """
        文生视频

        Args:
            prompt: 视频描述提示词
            model: 模型版本，默认 kling-v1
            duration: 视频时长 (秒)，支持 5/10
            resolution: 分辨率，支持 720p/1080p
            aspect_ratio: 宽高比，支持 16:9/9:16/1:1

        Returns:
            dict: {"task_id": "xxx", "status": "processing"}
        """
        token = self._get_access_token()
        if not token:
            return {"success": False, "error": "获取访问令牌失败"}

        try:
            url = f"{self.base_url}/v1/text2video"
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }

            payload = {
                "model": model,
                "prompt": prompt,
                "duration": duration,
                "resolution": resolution,
                "aspectRatio": aspect_ratio
            }

            response = requests.post(url, json=payload, headers=headers, timeout=60)
            result = response.json()

            if result.get("result") == 1:
                task_id = result["data"]["taskId"]
                logger.info(f"可灵 AI 视频生成任务已提交：{task_id}")
                return {"success": True, "task_id": task_id, "status": "processing"}
            else:
                logger.error(f"提交视频生成任务失败：{result}")
                return {"success": False, "error": result.get("error_msg", "未知错误")}

        except Exception as e:
            logger.error(f"提交视频生成任务异常：{e}")
            return {"success": False, "error": str(e)}

    def get_task_result(self, task_id: str) -> Dict[str, Any]:
        """
        查询任务结果

        Args:
            task_id: 任务 ID

        Returns:
            dict: 任务状态和结果
        """
        token = self._get_access_token()
        if not token:
            return {"success": False, "error": "获取访问令牌失败"}

        try:
            url = f"{self.base_url}/v1/task/{task_id}"
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }

            response = requests.get(url, headers=headers, timeout=30)
            result = response.json()

            if result.get("result") == 1:
                data = result["data"]
                status = data.get("status")  # processing, succeeded, failed
                return {
                    "success": True,
                    "status": status,
                    "video_url": data.get("videoUrl"),
                    "cover_url": data.get("coverUrl"),
                    "progress": data.get("progress", 0),
                    "error_message": data.get("errorMessage")
                }
            else:
                return {"success": False, "error": result.get("error_msg", "未知错误")}

        except Exception as e:
            logger.error(f"查询任务结果异常：{e}")
            return {"success": False, "error": str(e)}

    def wait_for_completion(self, task_id: str, timeout: int = 300, poll_interval: int = 5) -> Dict[str, Any]:
        """
        等待任务完成

        Args:
            task_id: 任务 ID
            timeout: 最大等待时间 (秒)
            poll_interval: 轮询间隔 (秒)

        Returns:
            dict: 最终结果
        """
        start_time = time.time()

        while time.time() - start_time < timeout:
            result = self.get_task_result(task_id)

            if not result["success"]:
                return result

            status = result["status"]
            if status == "succeeded":
                logger.info(f"视频生成完成：{task_id}")
                return result
            elif status == "failed":
                logger.error(f"视频生成失败：{task_id}, {result.get('error_message')}")
                return result

            logger.info(f"视频生成中... {task_id}, 进度：{result.get('progress', 0)}%")
            time.sleep(poll_interval)

        return {"success": False, "error": "任务超时"}
