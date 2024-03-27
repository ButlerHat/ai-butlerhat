from PIL import Image
import numpy as np
import imagehash

# Abrir las dos imágenes que quieres comparar con Pillow
image1 = Image.open("/workspaces/BUIBert/robotframework/Web/frontend/utils/borrar/Screenshot 2022-12-09 141347.png")
image2 = Image.open("/workspaces/BUIBert/robotframework/Web/frontend/utils/borrar/Screenshot 2022-12-09 141347.png")

# Obtener los histogramas de las imágenes
histogram1 = image1.histogram()
histogram2 = image2.histogram()

# Comparar los histogramas con la función isclose() de math
if np.allclose(histogram1, histogram2):
  print("Las imágenes son similares.")
else:
  print("Las imágenes no son similares.")

# Mesure the similarity between two images with hash
hash0 = imagehash.average_hash(image1)
hash1 = imagehash.average_hash(image2)

print(hash0 - hash1)
if hash0 - hash1 < 11:
  print("Las imágenes son similares.")
else:
    print("Las imágenes no son similares.")