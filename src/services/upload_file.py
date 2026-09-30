"""Завантаження аватарів у Cloudinary."""

import cloudinary
import cloudinary.uploader


class UploadFileService:
    """Сервіс для завантаження аватарів користувачів у Cloudinary."""

    def __init__(self, cloud_name, api_key, api_secret):
        """
        Налаштовує клієнт Cloudinary.

        Args:
            cloud_name: Назва хмари Cloudinary.
            api_key: API-ключ Cloudinary.
            api_secret: API-секрет Cloudinary.
        """
        self.cloud_name = cloud_name
        self.api_key = api_key
        self.api_secret = api_secret
        cloudinary.config(
            cloud_name=self.cloud_name,
            api_key=self.api_key,
            api_secret=self.api_secret,
            secure=True,
        )

    @staticmethod
    def upload_file(file, username) -> str:
        """
        Завантажує аватар і повертає його URL.

        Файл зберігається як ``RestApp/<username>``, тому нове завантаження
        замінює попередній аватар. Повернений URL веде на зображення,
        обрізане до розміру 250x250.

        Args:
            file: Завантажений файл із запиту.
            username: Власник аватара.

        Returns:
            Публічний URL завантаженого аватара.
        """
        public_id = f"RestApp/{username}"
        r = cloudinary.uploader.upload(file.file, public_id=public_id, overwrite=True)
        src_url = cloudinary.CloudinaryImage(public_id).build_url(
            width=250, height=250, crop="fill", version=r.get("version")
        )
        return src_url
