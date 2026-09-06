# 🚀🎬 ShortGPT 
## AI video automation framework
<p align="center">
  <a href="https://discord.gg/uERx39ru3R">
    <img src="https://dcbadge.vercel.app/api/server/uERx39ru3R?compact=true&style=flat">
  </a>
  <a href="https://star-history.com/#rayventura/shortgpt)">
    <img src="https://img.shields.io/github/stars/rayventura/shortgpt?style=social">
  </a>
  <a href="https://pypi.org/project/shortgpt/">
    <img src="https://static.pepy.tech/personalized-badge/shortgpt?period=month&units=international_system&left_color=blue&right_color=green&left_text=Downloads/month">
  </a>
  <a href="https://docs.shortgpt.ai/">
    <img src="https://img.shields.io/badge/docs-visit-blue">
  </a>  
</p>

<div align="center" style="border-radius: 20px;" width="18%">
    <img src="https://github.com/RayVentura/ShortGPT/assets/121462835/083c8dc3-bac5-42c1-a08d-3ff9686d18c5" alt="ShortGPT-logo" style="border-radius: 20px;" width="18%"/>
</div>
<div align="center">
  <a href="https://discord.gg/uERx39ru3R">
    <img src="https://img.shields.io/discord/1126042224979886160?color=7289da&logo=discord&logoColor=blue&labelColor=white&color=cyan" alt="Join our Discord" height="34">
  </a>
</div>

<div align="center">
⚡ Automating video and short content creation with AI ⚡
</div>
</br>

Follow the installation steps below for running the web app locally (running the google Colab is highly recommanded). 
Please read "installation-notes.md" for more details.
## 🎥 Showcase ([Full video on YouTube](https://youtu.be/hpoSHq-ER8U))

https://github.com/RayVentura/ShortGPT/assets/121462835/a802faad-0fd7-4fcb-aa82-6365c27ea5fe
## 🎥 Voice Dubbing


https://github.com/RayVentura/ShortGPT/assets/121462835/06f51b2d-f8b1-4a23-b299-55e0e18902ef

## 🌟 Show Your Support
We hope you find ShortGPT helpful! If you do, let us know by giving us a star ⭐ on the repo. It's easy, just click on the 'Star' button at the top right of the page. Your support means a lot to us and keeps us motivated to improve and expand ShortGPT. Thank you and happy content creating! 🎉 

[![GitHub star chart](https://img.shields.io/github/stars/rayventura/shortgpt?style=social)](https://github.com/RayVentura/ShortGPT/stargazers)
## 🛠️ How it works
![alt text](https://github.com/RayVentura/ShortGPT/assets/121462835/fcee74d4-f856-4481-949f-244558bf3bfa)
## 📝 Introduction to ShortGPT 
ShortGPT is a powerful framework for automating content creation. It simplifies video creation, footage sourcing, voiceover synthesis, and editing tasks. Of the most popular use-cases of ShortGPT is youtube automation and Tiktok creativity program automation.

- 🎞️ **Automated editing framework**: Streamlines the video creation process with an LLM oriented video editing language.

- 📃 **Scripts and Prompts**: Provides ready-to-use scripts and prompts for various LLM automated editing processes.

- 🗣️ **Voiceover / Content Creation**: Supports multiple languages including English 🇺🇸, Spanish 🇪🇸, Arabic 🇦🇪, French 🇫🇷, Polish 🇵🇱, German 🇩🇪, Italian 🇮🇹, Portuguese 🇵🇹, Russian 🇷🇺, Mandarin Chinese 🇨🇳, Japanese 🇯🇵, Hindi 🇮🇳,Korean 🇰🇷, and way over 30 more languages (with EdgeTTS)

- 🔗 **Caption Generation**: Automates the generation of video captions.

- 🌐🎥 **Asset Sourcing**: Sources images and video footage from the internet, connecting with the web and Pexels API as necessary.

---

# ⭐ Fork Additions — Custom Video Templates

This fork adds bespoke, isolated video templates that coexist with the default
ShortGPT pipelines. They live as **separate engines/scripts** so they never
interfere with the stock frames or each other.

## 🎯 WTD — "What's the Difference?" Explainer Template

The **WTD** template is Shalom's signature 30-second faceless explainer shorts:
a minimal stickman host (green beanie + red scarf) compares two concepts, X vs Y,
with the locked beat flow:

```
1. "This is X."            (concept X photo shown alone, stickman points)
2. "This is Y."            (both photos shown, stickman switches pose)
3. "What's the difference?"(both photos, stickman shrugs with "?" marks)
4-6. Plain-spoken explanation, no jargon
7. Closing takeaway
```

Then a fixed **subscribe end-card**: follow text + teal `@justthediff` handle
+ the SUBSCRIBE stickman holding a red sign.

### Files
- `wtd_compositor.py` — PIL frame + end-card renderer (text-safe auto-fit/wrap,
  transparent stickmen, fixed central position, dynamic concept-image registration,
  `@justthediff` watermark bottom-left).
- `make_wtd_single.py` — single-comparison builder (parameterized BEATS).
- `make_daily_finance.py` — **DWTD auto-generate pipeline** for the
  "Just The Difference" finance channel:
  → pick fresh topic from `wtd_topic_pool.json` → DeepSeek writes the 7 beats →
  2 Pexels concept photos → render 30s short with CTA end-card. Fully unattended.
- `pick_wtd_topic.py` — picker over the 526-topic finance pool (marks used).
- `wtd_topic_pool.json` — 526 finance "A vs B" topics (finance-only, high RPM).

### Runtime assets (OUTSIDE git, must exist)
- `/root/wtd_assets/stickmen_t/stick_1|2|3.png` — the 3 poses (point/point/ask)
- `/root/wtd_assets/stickmen_t/stick_subscribe.png` — transparent SUBSCRIBE stickman
- `/root/wtd_assets/finance/*.png` — concept photo thumbnails
- `PEXELS_API_KEY` in env (reads from `/root/AutoShorts-AI/.env`)
- LLM via freeinference `deepseek-v4-flash` (key from hermes `config.yaml`)
- Voice: `en-US-AndrewMultilingualNeural` (edge-tts)

### End-to-end daily generate
```bash
# dry-run (pick topic + show script, no render)
python3 make_daily_finance.py --dry

# make next video (marks topic used, writes file + _latest_wtd.json)
python3 make_daily_finance.py
```

### Uploading to "Just The Difference"
Upload path reuses `youtubeuploader` (see `shalom-dark-history/uploader/`).
Channel config: `uploader/channel_config.json`; auth token lives in
`uploader/request.token` (must be authorized to the finance channel).

---
*Everything above is additive to the upstream repo — the stock ShortGPT
pipelines (gaming secrets, dark history, tips, stock facts) are untouched and
still run independently.*

- 🧠 **Memory and persistency**: Ensures long-term persistency of automated editing variables with TinyDB.

## 🚀 Quick Start: Run ShortGPT on Google Colab (https://colab.research.google.com/drive/1_2UKdpF6lqxCqWaAcZb3rwMVQqtbisdE?usp=sharing)

If you prefer not to install the prerequisites on your local system, you can use the Google Colab notebook. This option is free and requires no installation setup.

1. Click on the link to the Google Colab notebook: [https://colab.research.google.com/drive/1_2UKdpF6lqxCqWaAcZb3rwMVQqtbisdE?usp=sharing](https://colab.research.google.com/drive/1_2UKdpF6lqxCqWaAcZb3rwMVQqtbisdE?usp=sharing)

2. Once you're in the notebook, simply run the cells in order from top to bottom. You can do this by clicking on each cell and pressing the 'Play' button, or by using the keyboard . Enjoy using ShortGPT!

# Instructions for running shortGPT locally
This guide provides step-by-step instructions for installing shortGPT and its dependencies.
To run ShortGPT locally, you need Docker.

## Installation Steps

To run ShortGPT, you need to have docker. Follow the instructions "installation-notes.md" for more details.

1. For running the Dockerfile, do this:
```bash
docker build -t short_gpt_docker:latest .
docker run -p 31415:31415 --env-file .env short_gpt_docker:latest
```
## Running runShortGPT.py Web Interface

2. After running the script, a Gradio interface should open at your local host on port 31415 (http://localhost:31415)
 

## Framework overview

- 🎬 The `ContentShortEngine` is designed for creating shorts, handling tasks from script generation to final rendering, including adding YouTube metadata.

- 🎥 The `ContentVideoEngine` is ideal for longer videos, taking care of tasks like generating audio, automatically sourcing background video footage, timing captions, and preparing background assets.

- 🗣️ The `ContentTranslationEngine` is designed to dub and translate entire videos, from mainstream languages to more specific target languages. It takes a video file, or youtube link, transcribe it's audio, translates the content, voices it in a target language, adds captions , and gives back a new video, in a totally different language.

- 🎞️ The automated `EditingEngine`, using Editing Markup Language and JSON, breaks down the editing process into manageable and customizable blocks, comprehensible to Large Language Models.

💡 ShortGPT offers customization options to suit your needs, from language selection to watermark addition.

🔧 As a framework, ShortGPT is adaptable and flexible, offering the potential for efficient, creative content creation.

More documentation incomming, please be patient.


## Technologies Used

ShortGPT utilizes the following technologies to power its functionality:

- **Moviepy**: Moviepy is used for video editing, allowing ShortGPT to make video editing and rendering

- **Openai**: Openai is used for automating the entire process, including generating scripts and prompts for LLM automated editing processes.

- **ElevenLabs**: ElevenLabs is used for voice synthesis, supporting multiple languages for voiceover creation.

- **EdgeTTS**: Microsoft's FREE EdgeTTS is used for voice synthesis, supporting way many more language than ElevenLabs currently.

- **Pexels**: Pexels is used for sourcing background footage, allowing ShortGPT to connect with the web and access a wide range of images and videos.

- **Bing Image**: Bing Image is used for sourcing images, providing a comprehensive database for ShortGPT to retrieve relevant visuals.

These technologies work together to provide a seamless and efficient experience in automating video and short content creation with AI.

## 💁 Contributing

As an open-source project in a rapidly developing field, we are extremely open to contributions, whether it would be in the form of a new feature, improved infrastructure, or better documentation.
<p align="center">
  <a href="https://star-history.com/#RayVentura/ShortGPT&Date">
    <img src="https://api.star-history.com/svg?repos=RayVentura/ShortGPT&type=Date" alt="Star History Chart">
  </a>
</p>
