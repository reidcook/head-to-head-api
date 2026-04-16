import os
import base64
import boto3

def upload_image_to_s3(name: str, base64_image: str) -> str:
    """Upload a base64 image to S3 and return the public URL."""
    # Strip the data URL prefix if present (e.g. "data:image/png;base64,")
    if "," in base64_image:
        header, data = base64_image.split(",", 1)
        ext = header.split("/")[1].split(";")[0]  # e.g. "png"
    else:
        data = base64_image
        ext = "png"

    image_bytes = base64.b64decode(data)
    bucket = os.environ["S3_BUCKET_NAME"]
    key = f"players/{name}.{ext}"

    # For local development
    if os.environ.get("AWS_ACCESS_KEY_ID"):
        s3 = boto3.client(
            "s3",
            aws_access_key_id=os.environ["AWS_ACCESS_KEY_ID"],
            aws_secret_access_key=os.environ["AWS_SECRET_ACCESS_KEY"],
            region_name=os.environ["AWS_REGION"],
        )
    # Already has creds in lambda
    else:
        s3 = boto3.client("s3")
    s3.put_object(Bucket=bucket, Key=key, Body=image_bytes, ContentType=f"image/{ext}")

    region = os.environ["AWS_REGION"]
    return f"https://{bucket}.s3.{region}.amazonaws.com/{key}"


# Helper to serialize MongoDB documents
def serialize_doc(doc):
    doc = dict(doc)
    if '_id' in doc:
        doc['_id'] = str(doc['_id'])
    return doc

SMASH_CHARS = [
    "Mario", "Donkey Kong", "Link", "Samus", "Dark Samus", "Yoshi", "Kirby", "Fox", "Pikachu", "Luigi", "Ness", "Captain Falcon", "Jigglypuff", "Peach", "Daisy", "Bowser", "Ice Climbers", "Sheik", "Zelda", "Dr. Mario", "Pichu", "Falco", "Marth", "Lucina", "Young Link", "Ganondorf", "Mewtwo", "Roy", "Chrom", "Mr. Game & Watch", "Meta Knight", "Pit", "Dark Pit", "Zero Suit Samus", "Wario", "Snake", "Ike", "Pokémon Trainer", "Diddy Kong", "Lucas", "Sonic", "King Dedede", "Olimar", "Lucario", "R.O.B.", "Toon Link", "Wolf", "Villager", "Mega Man", "Wii Fit Trainer", "Rosalina & Luma", "Little Mac", "Greninja", "Mii Brawler", "Mii Swordfighter", "Mii Gunner", "Palutena", "Pac-Man", "Robin", "Shulk", "Bowser Jr.", "Duck Hunt", "Ryu", "Ken", "Cloud", "Corrin", "Bayonetta", "Inkling", "Ridley", "Simon", "Richter", "King K. Rool", "Isabelle", "Incineroar", "Piranha Plant", "Joker", "Hero", "Banjo & Kazooie", "Terry", "Byleth", "Min Min", "Steve", "Sephiroth", "Pyra/Mythra", "Kazuya", "Sora"
]
