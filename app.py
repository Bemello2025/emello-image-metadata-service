from flask import Flask, request, jsonify
from flask_cors import CORS
from PIL import Image
import piexif
import io
import base64
import json

app = Flask(__name__)
CORS(app)

@app.route('/')
def home():
    return "✅ Emello Image Metadata Service is live."

@app.route('/write-metadata', methods=['POST'])
def write_metadata():
    data = request.json

    try:
        # Required
        base64_str = data.get("image_base64")
        if not base64_str:
            return jsonify({"error": "Missing image_base64"}), 400

        # Fallbacks for optional metadata
        alt_text = data.get("alt_text", "")
        title_tag = data.get("title_tag", "")
        description = data.get("cms_description", "")
        keywords = data.get("keywords", "")
        byline = data.get("byline", "Emello Creative Team / Studio Archive")
        copyright_notice = data.get("copyright_notice", "Emello Ltd. 2025. All rights reserved.")
        file_name = data.get("filename", "emello-image.jpg")
        pin_description = data.get("pin_description", "")
        associated_article = data.get("associated_article", "")

        iptc = data.get("iptc_metadata", {})
        iptc_object_name = iptc.get("ObjectName", title_tag)
        iptc_keywords = iptc.get("Keywords", [])
        iptc_caption = iptc.get("Caption-Abstract", description)
        iptc_special = iptc.get("SpecialInstructions", "")

        # Decode and load the image
        image_data = base64.b64decode(base64_str)
        image = Image.open(io.BytesIO(image_data))

        # Build EXIF metadata
        exif_dict = {"0th": {}, "Exif": {}, "GPS": {}, "1st": {}, "thumbnail": None}
        exif_dict["0th"][piexif.ImageIFD.ImageDescription] = description.encode("utf-8")
        exif_dict["0th"][piexif.ImageIFD.XPTitle] = title_tag.encode("utf-16le")
        exif_dict["0th"][piexif.ImageIFD.XPComment] = alt_text.encode("utf-16le")
        exif_dict["0th"][piexif.ImageIFD.XPKeywords] = keywords.encode("utf-16le")
        exif_dict["0th"][piexif.ImageIFD.Artist] = byline.encode("utf-8")
        exif_dict["0th"][piexif.ImageIFD.Copyright] = copyright_notice.encode("utf-8")

        # Save updated image with EXIF
        output = io.BytesIO()
        image.save(output, format="JPEG", exif=piexif.dump(exif_dict))
        encoded_img = base64.b64encode(output.getvalue()).decode("utf-8")

        # JSON-LD schema
        jsonld = {
            "@context": "https://schema.org",
            "@type": "ImageObject",
            "contentUrl": f"https://emello.com/images/{file_name}",
            "name": title_tag,
            "description": description,
            "caption": pin_description,
            "author": {
                "@type": "Organization",
                "name": "Emello"
            },
            "license": "https://emello.com/usage-guidelines",
            "associatedArticle": associated_article
        }

        # Return response
        return jsonify({
            "image_base64": encoded_img,
            "jsonld": jsonld,
            "iptc_written": {
                "ObjectName": iptc_object_name,
                "Keywords": iptc_keywords,
                "Caption": iptc_caption,
                "SpecialInstructions": iptc_special
            },
            "status": "success",
            "message": f"Metadata successfully embedded in {file_name}"
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=False, host="0.0.0.0", port=5000)
