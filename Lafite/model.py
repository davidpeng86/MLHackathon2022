import torch
import numpy as np
from PIL import Image as PIL_Image
import dnnlib, legacy
import clip
import time
import random
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By

s = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=s)
# driver.maximize_window()
driver.get('http://localhost:3000/')


class Generator:
    def __init__(self, device, path):
        self.name = 'generator'
        self.model = self.load_model(device, path)
        self.device = device
        if device == 'cpu':
            self.force_32 = True
        else:
            self.force_32 = False

    def load_model(self, device, path):
        with dnnlib.util.open_url(path) as f:
            network = legacy.load_network_pkl(f)
            self.G_ema = network['G_ema'].to(device)
            self.D = network['D'].to(device)
            if device == 'cpu':
                self.G_ema = self.G_ema.float()
            return self.G_ema

    def generate(self, z, c, fts, noise_mode='const', return_styles=True):
        return self.model(z, c, fts=fts, noise_mode=noise_mode, return_styles=return_styles, force_fp32=self.force_32)

    def generate_from_style(self, style, noise_mode='const'):
        ws = torch.randn(1, self.model.num_ws, 512)
        return self.model.synthesis(ws, fts=None, styles=style, noise_mode=noise_mode, force_fp32=self.force_32)

    def tensor_to_img(self, tensor):
        img = torch.clamp((tensor + 1.) * 127.5, 0., 255.)
        img_list = img.permute(0, 2, 3, 1)
        img_list = [img for img in img_list]
        return PIL_Image.fromarray(torch.cat(img_list, dim=-2).detach().cpu().numpy().astype(np.uint8))


change = ''
files = []

while True:
    with torch.no_grad():
        device = 'cpu'
        path = 'COCO2014_CLIP_ViTB32_all_text.pkl'
        generator = Generator(device=device, path=path)
        clip_model, _ = clip.load("ViT-B/32", device=device)
        clip_model = clip_model.eval()
        txt = str(driver.find_element(By.XPATH, '//*[@id="message"]').text).split('.')[-1]
        if txt != change and txt != '':
            print(txt)
            tokenized_text = clip.tokenize([txt]).to(device)
            txt_fts = clip_model.encode_text(tokenized_text)
            txt_fts = txt_fts / txt_fts.norm(dim=-1, keepdim=True)
            z = torch.randn((1, 512)).to(device)
            c = torch.randn((1, 1)).to(device)
            img, _ = generator.generate(z=z, c=c, fts=txt_fts)
            to_show_img = generator.tensor_to_img(img)
            filename = f"generated_{random.randrange(99999)}.jpg"
            save_path = f"../realtime-transcription/" + filename
            files.append(filename)
            to_show_img.save(save_path)
            driver.execute_script(
                f"document.getElementsByClassName('model_image')[0].src = 'http://localhost:3000/{filename}'"
            )
            time.sleep(0.5)
        change = txt
