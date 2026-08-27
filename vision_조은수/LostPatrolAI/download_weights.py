import os

from dotenv import load_dotenv
from roboflow import Roboflow

load_dotenv()

api_key = os.environ["ROBOFLOW_API_KEY"]

rf = Roboflow(api_key=api_key)
project = rf.workspace("-ym7za").project("lostitem-rgihn")
version = project.version(2)

models = version.models()
if not models:
    raise RuntimeError("This project version has no trained model yet.")

model = models[0]
print("model_type:", model.model_type)
weights_path = model.download(format="pt", location="weights")
print("weights saved to:", weights_path)
