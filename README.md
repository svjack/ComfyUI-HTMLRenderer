# ComfyUI-HTMLRenderer

## Install Chrome in Linux
```bash
### install chorme in linux
# wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
cp work/google-chrome-stable_current_amd64.deb .
sudo apt install ./google-chrome-stable_current_amd64.deb
google-chrome --version
# Google Chrome 145.0.7632.75 
which google-chrome
# wget https://storage.googleapis.com/chrome-for-testing-public/145.0.7632.75/linux64/chromedriver-linux64.zip
cp work/chromedriver-linux64.zip . 
unzip chromedriver-linux64.zip
sudo cp chromedriver-linux64/chromedriver /usr/local/bin/
sudo chmod +x /usr/local/bin/chromedriver
chromedriver --version
```

## Installtion
```bash
conda activate system
cd ComfyUI/custom_nodes
pip install playwright
playwright install chromium
git clone https://github.com/svjack/ComfyUI-HTMLRenderer
pip install -r ComfyUI-HTMLRenderer/requirements.txt
```

- HTMLFrameRenderer

<img width="1314" height="622" alt="捕获" src="https://github.com/user-attachments/assets/d58bc4c6-6ca9-415b-bc64-3555f1e69eb7" />

- HTMLVideoRecorderPlaywright

<img width="1704" height="695" alt="捕获" src="https://github.com/user-attachments/assets/f15146cd-415c-4ed2-b5fb-f57da3bf1dcd" />

