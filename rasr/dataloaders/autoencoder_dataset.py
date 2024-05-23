from torch.utils.data import Dataset
from torchvision import transforms
from PIL import Image

from rasr.util.fileio import get_list_of_files


class CustomAutoEncoderDataset(Dataset):
    def __init__(self, path, transforms=transforms.ToTensor()):
        self.files = get_list_of_files(path)
        self.transforms = transforms

    def __len__(self):
        return len(self.files)

    def __getitem__(self, idx):
        image = Image.open(self.files[idx])
        if self.transforms is not None:
            image = self.transforms(image)
        return image
