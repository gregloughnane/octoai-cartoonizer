import streamlit as st
from PIL import Image, ImageOps, ExifTags
from io import BytesIO
from base64 import b64decode, b64encode
import requests
import random
import webbrowser

CLIP_ENDPOINT = "https://cartoonizer-clip-test-4jkxk521l3v1.octoai.cloud"
SD_ENDPOINT = "https://cartoonizer-sd-demo-cgi-4jkxk521l3v1.octoai.cloud"

st.set_page_config(layout="wide", page_title="Cartoonizer")

# Powered by OctoML displayed in top right
st.markdown("""
<style>
.powered-by {
    position: absolute;
    top: -10px;
    right: 0;
    float: right;
}
.powered-by span {
    padding-right: 5;
</style>
<div class="powered-by">
<span>Powered by </span> <a href="https://octoai.cloud/"><img src="https://i.ibb.co/T1X1CHG/octoml-octo-ai-logo-vertical-container-white.png" alt="octoml-octo-ai-logo-vertical-container-white" border="0" width="200"></a>
</div>
""", unsafe_allow_html=True)

# PIL helper
def crop_center(pil_img, crop_width, crop_height):
    img_width, img_height = pil_img.size
    return pil_img.crop(((img_width - crop_width) // 2,
                         (img_height - crop_height) // 2,
                         (img_width + crop_width) // 2,
                         (img_height + crop_height) // 2))

# PIL helper
def crop_max_square(pil_img):
    return crop_center(pil_img, min(pil_img.size), min(pil_img.size))

# Download the fixed image
def convert_image(img):
    buf = BytesIO()
    img.save(buf, format="PNG")
    byte_im = buf.getvalue()
    return byte_im

def cartoonize_image(upload, strength, seed, extra_desc):
    input_img = Image.open(upload)
    try:
        # Rotate based on Exif Data
        for orientation in ExifTags.TAGS.keys():
            if ExifTags.TAGS[orientation]=='Orientation':
                break
        exif = input_img._getexif()
        if exif[orientation] == 3:
            input_img=input_img.rotate(180, expand=True)
        elif exif[orientation] == 6:
            input_img=input_img.rotate(270, expand=True)
        elif exif[orientation] == 8:
            input_img=input_img.rotate(90, expand=True)
    except:
        # Do nothing
        print("No rotation to perform based on Exif data")
    # Apply cropping and resizing to work on a square image
    cropped_img = crop_max_square(input_img)
    resized_img = cropped_img.resize((512, 512))
    col1.write("Original Image :camera:")
    col1.image(resized_img)

    # Prepare the JSON query to send to OctoAI's inference endpoint
    buffer = BytesIO()
    resized_img.save(buffer, format="png")
    image_out_bytes = buffer.getvalue()
    image_out_b64 = b64encode(image_out_bytes)

    # Prepare CLIP request
    clip_request = {
        "mode": "fast",
        "image": image_out_b64.decode("utf8"),
    }
    # Send to CLIP endpoint
    reply = requests.post(
        "{}/predict".format(CLIP_ENDPOINT),
        headers={"Content-Type": "application/json"},
        json=clip_request
    )
    # Retrieve prompt
    clip_reply = reply.json()["completion"]["labels"]

    prompt = extra_desc + ", " + clip_reply

    # Prepare SD request for img2img
    sd_request = {
        "image": image_out_b64.decode("utf8"),
        "prompt": prompt,
        "strength": float(strength)/10,
        # The rest below is hard coded
        "negative_prompt": "EasyNegative, drawn by bad-artist, sketch by bad-artist-anime, (bad_prompt:0.8), (artist name, signature, watermark:1.4), (ugly:1.2), (worst quality, poor details:1.4), bad-hands-5, badhandv4, blurry, nsfw",
        "model": "cgi",
        "vae": "YOZORA.vae.pt",
        "sampler": "K_EULER_ANCESTRAL",
        "cfg_scale": 7,
        "num_images": 1,
        "seed": seed,
        "width": 512,
        "height": 512,
        "steps": 20
    }
    reply = requests.post(
        "{}/predict".format(SD_ENDPOINT),
        headers={"Content-Type": "application/json"},
        json=sd_request
    )

    img_bytes = b64decode(reply.json()["completion"]["image_0"])
    cartoonized = Image.open(BytesIO(img_bytes), formats=("png",))

    col2.write("Transformed Image :star2:")
   
    # open octoml logo image for watermark
    watermark = Image.open("assets/octoml-octopus-white.png")
    watermark = watermark.resize((100, 100)) # change the numbers to adjust the size

    A = watermark.getchannel('A')

    # Make all opaque pixels into semi-opaque
    newA = A.point(lambda i: 35 if i>0 else 0)

    # Put new alpha channel back into original image and save
    watermark.putalpha(newA)

    # add watermark to image
    watermarked_image = cartoonized.convert("RGBA")
    watermarked_image.paste(watermark, (0,0), watermark)
    watermarked_image.save("cartoonized_marked.png", quality=90)

    col2.image(watermarked_image)

st.title("🤩 Cartoonizer")

# initialize the session state variables
if "seed" not in st.session_state:
    st.session_state.seed = 0
if "strength" not in st.session_state:
    st.session_state.strength = 4
if "extra_desc" not in st.session_state:
    st.session_state.extra_desc = ""

# create a placeholder for the image
image_placeholder = st.empty()

# take image
my_upload = image_placeholder.camera_input('📸 Take a picture!')

# update the session state variables with the user input
if my_upload is not None:
    image_placeholder.empty()
    st.session_state.my_upload = my_upload

# break the display into two columns
col1, col2 = st.columns(2)

# once image is taken, pop up cropped image and cartoonized image, with ability to modify
if my_upload is not None:

    with col2:

        # show cartoonized image
        cartoonize_image(st.session_state.my_upload, st.session_state.strength, st.session_state.seed, st.session_state.extra_desc)
        
        # button - generate new variation
        if st.button('😊 Generate New Variation!'):
            # update the seed value with a random number
            st.session_state.seed = random.randint(0, 1024)

        # slider - increase creativity of image
        st.session_state.strength = st.slider(
            ":brain: Imagination Slider (lower: closer to original, higher: more imaginative result)",
            3, 10, 4)
        
        # optional text box for Stable Diffusion inputs, hidden until expanded
        with st.expander("🖋️ Add more context to customize the output"):
            # update the extra_desc value with the text input
            st.session_state.extra_desc = st.text_input("")
    
        # create a button widget that calls the rerun function when clicked
        if st.button("🔄 Restart"):
            webbrowser.open("https://cartoonizer-octo-ai4.streamlit.app/")


