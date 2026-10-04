from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.utils.deconstruct import deconstructible


@deconstructible
class PrivateFileSystemStorage(FileSystemStorage):
	def __init__(self, location=None, *args, **kwargs):
		super().__init__(location or settings.PRIVATE_MEDIA_ROOT, *args, **kwargs)


private_storage = PrivateFileSystemStorage()