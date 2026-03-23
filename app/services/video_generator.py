"""
GitHub Trending 视频生成服务
支持 FFmpeg 本地生成和可灵 AI 云生成
"""
import os
import logging
import subprocess
import shutil
from datetime import datetime
from typing import Dict, List, Optional
from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)


class VideoGenerator:
    """视频生成器"""

    def __init__(self, config):
        self.config = config
        # 支持 Flask config 字典和 Config 对象两种访问方式
        self.output_dir = getattr(config, 'VIDEO_OUTPUT_DIR', None) or config.get('VIDEO_OUTPUT_DIR', './videos')
        self.temp_dir = os.path.join(self.output_dir, 'temp')
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(self.temp_dir, exist_ok=True)

        # 可灵 AI 配置
        self.kling_app_key = getattr(config, 'KLING_APP_KEY', None) or config.get('KLING_APP_KEY')
        self.kling_app_secret = getattr(config, 'KLING_APP_SECRET', None) or config.get('KLING_APP_SECRET')
        self.use_kling = bool(self.kling_app_key and self.kling_app_secret)

        # 初始化可灵 AI 客户端
        if self.use_kling:
            from app.services.kling_ai import KlingAIClient
            self.kling_client = KlingAIClient(self.kling_app_key, self.kling_app_secret)
            logger.info("可灵 AI 客户端已初始化")
        else:
            self.kling_client = None
            logger.info("可灵 AI 未配置，使用本地 FFmpeg 生成")

        # 检查 FFmpeg 是否可用
        self.ffmpeg_available = self._check_ffmpeg()

    def _check_ffmpeg(self) -> bool:
        """检查 FFmpeg 是否可用"""
        try:
            result = subprocess.run(
                ['ffmpeg', '-version'],
                capture_output=True,
                timeout=5
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False

    def generate_video(self, script, images: Optional[List] = None, bgm_path: Optional[str] = None) -> Dict:
        """
        生成视频

        Args:
            script: VideoScript 对象，包含文案内容
            images: 图片列表，用于视频素材
            bgm_path: 背景音乐文件路径

        Returns:
            dict: {'video_path': str, 'video_url': str}
        """
        logger.info(f"开始生成视频：{script.script_title}")

        # 优先使用可灵 AI 生成（如果已配置）
        if self.use_kling and self.kling_client:
            return self._generate_video_by_kling(script)

        # 使用本地 FFmpeg 生成
        return self._generate_video_by_ffmpeg(script, images, bgm_path)

    def _generate_video_by_kling(self, script) -> Dict:
        """
        使用可灵 AI 生成视频

        Args:
            script: VideoScript 对象

        Returns:
            dict: {'video_path': str, 'video_url': str}
        """
        logger.info("使用可灵 AI 生成视频...")

        try:
            # 构建视频生成提示词
            prompt = self._build_kling_prompt(script)

            # 提交任务
            result = self.kling_client.text_to_video(
                prompt=prompt,
                model="kling-v1",
                duration=10,  # 10 秒
                resolution="720p",
                aspect_ratio="16:9"
            )

            if not result.get("success"):
                raise RuntimeError(f"提交可灵 AI 任务失败：{result.get('error')}")

            task_id = result["task_id"]
            logger.info(f"可灵 AI 任务已提交：{task_id}，等待完成...")

            # 等待任务完成
            final_result = self.kling_client.wait_for_completion(task_id, timeout=600, poll_interval=10)

            if not final_result.get("success"):
                raise RuntimeError(f"可灵 AI 任务失败：{final_result.get('error')}")

            if final_result.get("status") != "succeeded":
                raise RuntimeError(f"可灵 AI 任务状态异常：{final_result.get('status')}")

            video_url = final_result.get("video_url")
            if not video_url:
                raise RuntimeError("可灵 AI 未返回视频 URL")

            # 下载视频到本地
            video_path = self._download_kling_video(video_url, script.project_id)

            logger.info(f"可灵 AI 视频下载完成：{video_path}")

            return {
                'video_path': video_path,
                'video_url': f'/videos/{os.path.basename(video_path)}'
            }

        except Exception as e:
            logger.error(f"可灵 AI 生成视频失败：{e}")
            # 降级到本地 FFmpeg 生成
            logger.info("降级到本地 FFmpeg 生成...")
            return self._generate_video_by_ffmpeg(script, None, None)

    def _build_kling_prompt(self, script) -> str:
        """
        构建可灵 AI 视频生成提示词

        Args:
            script: VideoScript 对象

        Returns:
            str: 优化后的提示词
        """
        # 提取关键信息
        title = script.script_title or "项目介绍"
        content = script.script_content or ""
        highlights = script.key_highlights or ""

        # 构建详细描述
        prompt = f"""
这是一个科技类短视频，介绍一个优秀的开源项目。

视频主题：{title}

项目特色：
{highlights}

视频风格要求：
1. 现代科技感，简洁专业的视觉风格
2. 蓝色或深色背景，体现科技感
3. 包含代码展示、界面演示等元素
4. 流畅的转场和动效
5. 适合 B 站、抖音等短视频平台

视频节奏：
- 开场 2 秒：吸引眼球的标题动画
- 中间 6 秒：项目特色展示，包含代码/界面演示
- 结尾 2 秒：总结和行动号召

整体氛围：专业、现代、科技感十足
""".strip()

        return prompt

    def _download_kling_video(self, video_url: str, project_id: int) -> str:
        """
        下载可灵 AI 生成的视频到本地

        Args:
            video_url: 视频 URL
            project_id: 项目 ID

        Returns:
            str: 本地视频路径
        """
        import requests

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        video_filename = f"kling_video_{project_id}_{timestamp}.mp4"
        video_path = os.path.join(self.output_dir, video_filename)

        # 下载视频
        response = requests.get(video_url, stream=True, timeout=60)
        response.raise_for_status()

        with open(video_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        logger.info(f"视频已下载到：{video_path}")
        return video_path

    def _generate_video_by_ffmpeg(self, script, images: Optional[List] = None, bgm_path: Optional[str] = None) -> Dict:
        """
        使用 FFmpeg 生成视频（原有逻辑）
        """

        # 准备素材
        project_id = script.project_id
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        video_filename = f"video_{project_id}_{timestamp}.mp4"
        video_path = os.path.join(self.output_dir, video_filename)

        # 生成视频素材
        temp_video_dir = os.path.join(self.temp_dir, f"temp_{project_id}_{timestamp}")
        os.makedirs(temp_video_dir, exist_ok=True)

        try:
            # 1. 生成字幕文件
            subtitle_path = self._generate_subtitle(script, temp_video_dir)

            # 2. 准备图片/视频素材
            if images:
                image_paths = self._prepare_images(images, temp_video_dir)
            else:
                # 没有提供图片时，生成纯色背景或从文案生成简单画面
                image_paths = self._generate_placeholder_images(script, temp_video_dir)

            # 3. 生成视频片段
            video_clips = self._generate_video_clips(image_paths, subtitle_path, temp_video_dir)

            # 4. 合并视频片段
            self._merge_video_clips(video_clips, video_path, bgm_path)

            # 5. 清理临时文件
            self._cleanup_temp(temp_video_dir)

            logger.info(f"视频生成完成：{video_path}")

            return {
                'video_path': video_path,
                'video_url': f'/videos/{video_filename}'
            }

        except Exception as e:
            logger.error(f"视频生成失败：{e}")
            # 保留临时文件用于调试
            raise

    def _generate_subtitle(self, script, output_dir: str) -> str:
        """
        生成字幕文件（SRT 格式）

        Args:
            script: VideoScript 对象
            output_dir: 输出目录

        Returns:
            str: 字幕文件路径
        """
        subtitle_path = os.path.join(output_dir, 'subtitle.srt')

        # 解析文案内容，生成时间轴
        content = script.script_content or ''
        lines = content.split('\n')

        # 估算每行的时间（假设每秒 3 个字）
        words_per_second = 3
        start_time = 0

        with open(subtitle_path, 'w', encoding='utf-8') as f:
            index = 1
            for line in lines:
                line = line.strip()
                if not line:
                    continue

                # 计算持续时间
                duration = max(2, len(line) // words_per_second)
                end_time = start_time + duration

                # 写入 SRT 格式
                f.write(f"{index}\n")
                f.write(f"{self._format_srt_time(start_time)} --> {self._format_srt_time(end_time)}\n")
                f.write(f"{line}\n\n")

                index += 1
                start_time = end_time

        logger.info(f"字幕文件已生成：{subtitle_path}")
        return subtitle_path

    def _format_srt_time(self, seconds: int) -> str:
        """将秒数转换为 SRT 时间格式 (HH:MM:SS,mmm)"""
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        return f"{hours:02d}:{minutes:02d}:{secs:02d},000"

    def _prepare_images(self, images: List, output_dir: str) -> List[str]:
        """
        准备图片素材

        Args:
            images: 图片信息列表（ImageAsset 对象或 dict）
            output_dir: 输出目录

        Returns:
            List[str]: 图片文件路径列表
        """
        image_paths = []

        for i, img in enumerate(images):
            if isinstance(img, dict):
                img_path = img.get('image_path', '')
                img_url = img.get('image_url', '')
            else:
                img_path = getattr(img, 'image_path', '')
                img_url = getattr(img, 'image_url', '')

            # 检查图片是否存在
            actual_path = None
            if img_path and os.path.exists(img_path):
                actual_path = img_path
            elif img_url:
                # 如果是相对路径 URL，转换为本地路径
                if img_url.startswith('/'):
                    actual_path = img_url.lstrip('/')

            if actual_path and os.path.exists(actual_path):
                image_paths.append(actual_path)
            else:
                logger.warning(f"图片不存在：{img_path or img_url}")

        return image_paths

    def _generate_placeholder_images(self, script, output_dir: str) -> List[str]:
        """
        生成占位图片（当没有提供图片素材时）

        使用 Pillow 生成多场景画面：标题页 + 关键亮点页 + 结尾页

        Args:
            script: VideoScript 对象
            output_dir: 输出目录

        Returns:
            List[str]: 生成的图片路径列表
        """
        import json

        placeholder_paths = []

        # 背景颜色方案（不同场景使用不同颜色）
        bg_colors = [
            ('#1a3a5c', '#2d5a87'),  # 深蓝渐变
            ('#1a4a3c', '#2d7a57'),  # 深绿渐变
            ('#4a1a3c', '#7a2d57'),  # 深紫渐变
            ('#3a3a1c', '#5a5a2d'),  # 深黄渐变
        ]

        try:
            # 1. 生成标题画面
            title = script.script_title or f"Project {script.project_id}"
            title_path = os.path.join(output_dir, 'title.png')
            self._create_title_card(title, title_path, bg_colors[0])
            placeholder_paths.append(title_path)
            logger.info(f"标题画面已生成：{title_path}")

            # 2. 生成关键亮点画面
            highlights = []
            if script.key_highlights:
                try:
                    highlights = json.loads(script.key_highlights)
                except (json.JSONDecodeError, TypeError):
                    highlights = []

            for i, highlight in enumerate(highlights[:4]):  # 最多 4 个亮点
                highlight_path = os.path.join(output_dir, f'highlight_{i+1}.png')
                bg_color = bg_colors[(i + 1) % len(bg_colors)]

                hl_title = highlight.get('title', f'亮点 {i+1}')
                hl_desc = highlight.get('description', '')

                self._create_highlight_card(hl_title, hl_desc, highlight_path, bg_color)
                placeholder_paths.append(highlight_path)
                logger.info(f"亮点画面 {i+1} 已生成：{highlight_path}")

            # 3. 生成文案摘要画面（如果有长文案）
            content = script.script_content or ''
            if len(content) > 100:
                # 提取文案中的关键段落
                lines = [line.strip() for line in content.split('\n') if line.strip()]
                # 选择 2-3 个关键句子
                key_sentences = [l for l in lines if len(l) > 10 and len(l) < 80][:2]

                if key_sentences:
                    summary_path = os.path.join(output_dir, 'summary.png')
                    bg_color = bg_colors[2]
                    self._create_summary_card(key_sentences, summary_path, bg_color)
                    placeholder_paths.append(summary_path)
                    logger.info(f"摘要画面已生成：{summary_path}")

            # 4. 生成结尾画面
            end_path = os.path.join(output_dir, 'end.png')
            end_title = "感谢观看"
            end_subtitle = script.call_to_action or "点赞 | 关注 | 分享"
            self._create_end_card(end_title, end_subtitle, end_path, bg_colors[3])
            placeholder_paths.append(end_path)
            logger.info(f"结尾画面已生成：{end_path}")

        except Exception as e:
            logger.warning(f"生成占位画面失败：{e}")
            # 如果生成失败，至少返回一个标题画面
            if not placeholder_paths:
                try:
                    title = script.script_title or f"Project {script.project_id}"
                    title_path = os.path.join(output_dir, 'title.png')
                    self._create_title_card(title, title_path, bg_colors[0])
                    placeholder_paths.append(title_path)
                except:
                    pass

        return placeholder_paths

    def _create_title_card(self, title: str, output_path: str, bg_color: tuple):
        """创建标题卡片"""
        img = Image.new('RGB', (1920, 1080), color=bg_color[0])
        draw = ImageDraw.Draw(img)

        # 创建渐变背景
        for y in range(1080):
            r = int(int(bg_color[0][1:3], 16) + (int(bg_color[1][1:3], 16) - int(bg_color[0][1:3], 16)) * y / 1080)
            g = int(int(bg_color[0][3:5], 16) + (int(bg_color[1][3:5], 16) - int(bg_color[0][3:5], 16)) * y / 1080)
            b = int(int(bg_color[0][5:7], 16) + (int(bg_color[1][5:7], 16) - int(bg_color[0][5:7], 16)) * y / 1080)
            draw.line([(0, y), (1920, y)], fill=(r, g, b))

        # 加载字体
        font_large = self._load_chinese_font(72)
        font_medium = self._load_chinese_font(42)

        # 绘制标题（居中）
        title_bbox = draw.textbbox((0, 0), title, font=font_large)
        title_width = title_bbox[2] - title_bbox[0]
        title_x = (1920 - title_width) // 2
        title_y = 400
        draw.text((title_x, title_y), title, fill='white', font=font_large)

        # 绘制副标题
        subtitle = "GitHub Trending 项目推荐"
        sub_bbox = draw.textbbox((0, 0), subtitle, font=font_medium)
        sub_width = sub_bbox[2] - sub_bbox[0]
        sub_x = (1920 - sub_width) // 2
        draw.text((sub_x, 520), subtitle, fill='#cccccc', font=font_medium)

        img.save(output_path, 'PNG')

    def _create_highlight_card(self, hl_title: str, hl_desc: str, output_path: str, bg_color: tuple):
        """创建亮点卡片"""
        img = Image.new('RGB', (1920, 1080), color=bg_color[0])
        draw = ImageDraw.Draw(img)

        # 创建渐变背景
        for y in range(1080):
            r = int(int(bg_color[0][1:3], 16) + (int(bg_color[1][1:3], 16) - int(bg_color[0][1:3], 16)) * y / 1080)
            g = int(int(bg_color[0][3:5], 16) + (int(bg_color[1][3:5], 16) - int(bg_color[0][3:5], 16)) * y / 1080)
            b = int(int(bg_color[0][5:7], 16) + (int(bg_color[1][5:7], 16) - int(bg_color[0][5:7], 16)) * y / 1080)
            draw.line([(0, y), (1920, y)], fill=(r, g, b))

        # 加载字体
        font_title = self._load_chinese_font(56)
        font_desc = self._load_chinese_font(36)

        # 绘制标题
        title_bbox = draw.textbbox((0, 0), hl_title, font=font_title)
        title_width = title_bbox[2] - title_bbox[0]
        title_x = (1920 - title_width) // 2
        draw.text((title_x, 200), hl_title, fill='#ffffff', font=font_title)

        # 绘制描述（自动换行）
        margin = 150
        max_width = 1920 - 2 * margin
        wrapped_lines = self._wrap_text(hl_desc, font_desc, max_width)

        y_position = 350
        for line in wrapped_lines[:6]:  # 最多显示 6 行
            line_bbox = draw.textbbox((0, 0), line, font=font_desc)
            line_width = line_bbox[2] - line_bbox[0]
            line_x = (1920 - line_width) // 2
            draw.text((line_x, y_position), line, fill='#e0e0e0', font=font_desc)
            y_position += 50

        img.save(output_path, 'PNG')

    def _create_summary_card(self, sentences: List[str], output_path: str, bg_color: tuple):
        """创建摘要卡片"""
        img = Image.new('RGB', (1920, 1080), color=bg_color[0])
        draw = ImageDraw.Draw(img)

        # 创建渐变背景
        for y in range(1080):
            r = int(int(bg_color[0][1:3], 16) + (int(bg_color[1][1:3], 16) - int(bg_color[0][1:3], 16)) * y / 1080)
            g = int(int(bg_color[0][3:5], 16) + (int(bg_color[1][3:5], 16) - int(bg_color[0][3:5], 16)) * y / 1080)
            b = int(int(bg_color[0][5:7], 16) + (int(bg_color[1][5:7], 16) - int(bg_color[0][5:7], 16)) * y / 1080)
            draw.line([(0, y), (1920, y)], fill=(r, g, b))

        # 加载字体
        font_title = self._load_chinese_font(48)

        # 绘制标题
        title = "项目特色"
        title_bbox = draw.textbbox((0, 0), title, font=font_title)
        title_width = title_bbox[2] - title_bbox[0]
        title_x = (1920 - title_width) // 2
        draw.text((title_x, 150), title, fill='#ffffff', font=font_title)

        # 绘制句子列表
        y_position = 300
        for i, sentence in enumerate(sentences):
            item_text = f"  {i+1}. {sentence}"
            item_bbox = draw.textbbox((0, 0), item_text, font=font_title)
            item_x = 200
            draw.text((item_x, y_position), item_text, fill='#e0e0e0', font=font_title)
            y_position += 80

        img.save(output_path, 'PNG')

    def _create_end_card(self, title: str, subtitle: str, output_path: str, bg_color: tuple):
        """创建结尾卡片"""
        img = Image.new('RGB', (1920, 1080), color=bg_color[0])
        draw = ImageDraw.Draw(img)

        # 创建渐变背景
        for y in range(1080):
            r = int(int(bg_color[0][1:3], 16) + (int(bg_color[1][1:3], 16) - int(bg_color[0][1:3], 16)) * y / 1080)
            g = int(int(bg_color[0][3:5], 16) + (int(bg_color[1][3:5], 16) - int(bg_color[0][3:5], 16)) * y / 1080)
            b = int(int(bg_color[0][5:7], 16) + (int(bg_color[1][5:7], 16) - int(bg_color[0][5:7], 16)) * y / 1080)
            draw.line([(0, y), (1920, y)], fill=(r, g, b))

        # 加载字体
        font_large = self._load_chinese_font(72)
        font_medium = self._load_chinese_font(42)

        # 绘制主标题
        title_bbox = draw.textbbox((0, 0), title, font=font_large)
        title_width = title_bbox[2] - title_bbox[0]
        title_x = (1920 - title_width) // 2
        draw.text((title_x, 400), title, fill='white', font=font_large)

        # 绘制副标题
        sub_bbox = draw.textbbox((0, 0), subtitle, font=font_medium)
        sub_width = sub_bbox[2] - sub_bbox[0]
        sub_x = (1920 - sub_width) // 2
        draw.text((sub_x, 550), subtitle, fill='#cccccc', font=font_medium)

        img.save(output_path, 'PNG')

    def _load_chinese_font(self, size: int):
        """加载中文字体"""
        font_paths = [
            '/System/Library/Fonts/STHeiti Medium.ttc',
            '/System/Library/Fonts/Hiragino Sans GB.ttc',
            '/System/Library/Fonts/PingFang.ttc',
        ]
        for font_path in font_paths:
            if os.path.exists(font_path):
                try:
                    return ImageFont.truetype(font_path, size)
                except:
                    continue
        logger.warning(f"未找到中文字体，使用默认字体 (size={size})")
        return ImageFont.load_default()

    def _wrap_text(self, text: str, font, max_width: int) -> List[str]:
        """文本自动换行"""
        words = text.replace(',', ', ').replace(',, ', ', ').split(' ')
        lines = []
        current_line = ""

        for word in words:
            test_line = current_line + word if not current_line else current_line + " " + word
            bbox = font.getbbox(test_line)
            if bbox[2] - bbox[0] <= max_width:
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line)
                current_line = word

        if current_line:
            lines.append(current_line)

        return lines

    def _generate_video_clips(self, image_paths: List[str], subtitle_path: str, output_dir: str) -> List[str]:
        """
        为每个图片生成视频片段（带字幕和转场效果）

        Args:
            image_paths: 图片路径列表
            subtitle_path: 字幕文件路径
            output_dir: 输出目录

        Returns:
            List[str]: 视频片段路径列表
        """
        video_clips = []

        # 根据画面类型分配不同的时长
        # title/end 画面显示 3 秒，highlight 画面显示 5 秒，summary 画面显示 4 秒
        for i, img_path in enumerate(image_paths):
            clip_path = os.path.abspath(os.path.join(output_dir, f'clip_{i}.mp4'))

            # 根据文件名判断画面类型，设置不同时长
            if 'title' in img_path or 'end' in img_path:
                clip_duration = 3
            elif 'highlight' in img_path:
                clip_duration = 5
            elif 'summary' in img_path:
                clip_duration = 4
            else:
                clip_duration = 4  # 默认 4 秒

            # 添加淡入淡出转场效果
            fade_in_duration = 0.5  # 淡入 0.5 秒
            fade_out_duration = 0.5  # 淡出 0.5 秒

            cmd = [
                'ffmpeg', '-y',
                '-loop', '1',
                '-i', img_path,
                '-c:v', 'h264_videotoolbox' if self._check_videotoolbox() else 'libx264',
                '-t', str(clip_duration),
                '-pix_fmt', 'yuv420p',
                '-vf', f'scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2,fade=in:st=0:d={fade_in_duration},fade=out:st={clip_duration-fade_out_duration}:d={fade_out_duration}',
                '-c:a', 'aac',
                '-b:a', '128k',
                clip_path
            ]

            try:
                subprocess.run(cmd, capture_output=True, timeout=60, check=True)
                video_clips.append(clip_path)
                logger.info(f"视频片段已生成：{clip_path} ({clip_duration}秒)")
            except subprocess.CalledProcessError as e:
                logger.error(f"生成视频片段失败 {img_path}: {e.stderr.decode() if e.stderr else str(e)}")

        return video_clips

    def _check_videotoolbox(self) -> bool:
        """检查是否支持 VideoToolbox 硬件加速（macOS）"""
        try:
            result = subprocess.run(
                ['ffmpeg', '-encoders'],
                capture_output=True,
                text=True,
                timeout=5
            )
            return 'h264_videotoolbox' in result.stdout
        except:
            return False

    def _merge_video_clips(self, video_clips: List[str], output_path: str, bgm_path: Optional[str] = None):
        """
        合并视频片段

        Args:
            video_clips: 视频片段路径列表
            output_path: 输出路径
            bgm_path: 背景音乐路径
        """
        if not video_clips:
            raise ValueError("没有可合并的视频片段")

        # 创建文件列表
        list_file = os.path.join(self.temp_dir, 'merge_list.txt')
        with open(list_file, 'w') as f:
            for clip_path in video_clips:
                f.write(f"file '{clip_path}'\n")

        # 合并视频
        cmd = [
            'ffmpeg', '-y',
            '-f', 'concat',
            '-safe', '0',
            '-i', list_file,
            '-c:v', 'h264_videotoolbox' if self._check_videotoolbox() else 'libx264',
            '-c:a', 'aac',
            '-b:a', '128k',
            '-pix_fmt', 'yuv420p',
            output_path
        ]

        # 如果有背景音乐，添加音频
        if bgm_path and os.path.exists(bgm_path):
            # 需要重新处理以添加音频
            temp_output = output_path + '.temp.mp4'
            cmd_with_audio = [
                'ffmpeg', '-y',
                '-i', output_path,
                '-i', bgm_path,
                '-c:v', 'copy',
                '-c:a', 'aac',
                '-b:a', '128k',
                '-shortest',
                output_path
            ]
            try:
                subprocess.run(cmd, capture_output=True, timeout=300, check=True)
                subprocess.run(cmd_with_audio, capture_output=True, timeout=300, check=True)
                return
            except subprocess.CalledProcessError as e:
                logger.warning(f"添加背景音乐失败：{e}，使用无音频版本")

        # 无背景音乐或添加失败
        try:
            subprocess.run(cmd, capture_output=True, timeout=300, check=True)
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"合并视频失败：{e}")

    def _cleanup_temp(self, temp_dir: str):
        """清理临时文件"""
        try:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
                logger.info(f"已清理临时目录：{temp_dir}")
        except Exception as e:
            logger.warning(f"清理临时文件失败：{e}")

    def check_status(self, task_id: int) -> Dict:
        """
        检查视频生成状态

        Args:
            task_id: 任务 ID

        Returns:
            dict: {'status': str, 'progress': int}
        """
        # 简单实现，实际应该查询任务状态
        return {
            'status': 'completed',
            'progress': 100
        }

    def get_capabilities(self) -> Dict:
        """
        获取视频生成能力说明

        Returns:
            dict: 能力说明
        """
        return {
            'ffmpeg_available': self.ffmpeg_available,
            'features': [
                '图片转视频',
                '字幕生成',
                '视频合并',
                '背景音乐'
            ],
            'limitations': [
                '需要安装 FFmpeg',
                '不支持 AI 语音合成（需额外配置）',
                '不支持自动镜头转场（需手动配置）'
            ],
            'requirements': {
                'ffmpeg': '>=4.0',
                'python': '>=3.8'
            },
            'installation': {
                'macOS': 'brew install ffmpeg',
                'ubuntu': 'sudo apt-get install ffmpeg',
                'windows': '从 https://ffmpeg.org/download.html 下载'
            }
        }
