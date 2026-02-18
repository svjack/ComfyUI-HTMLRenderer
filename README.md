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
git clone https://github.com/svjack/ComfyUI-HTMLRenderer
pip install -r ComfyUI-HTMLRenderer/requirements.txt
```
