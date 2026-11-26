import serial
import matplotlib.pyplot as plt
import numpy as np

baud_rate = 115200
port = "COM4"
ser = serial.Serial(port, baud_rate)
data = {}

while True:
    # Luetaan rivi serialista ja muutetaan se string tyypiksi
    line = ser.readline().decode(errors="ignore").strip()
    print(line)

    # Ei huomioida tyhjiä rivejä
    if not line:
        continue

    # Laitetaan string osiin (tyhjä väli toimii erottaja merkkinä)
    parts = line.split()

    # Rivi, joka sisältää 7 osaa, ja alkaa kirjaimilla "cp" on confusion matrix rivi
    if len(parts) == 7 and parts[0].startswith("cp"):
        try:
            # Erotellaan arvot rivin osista
            values = [int(x) for x in parts[1:]]

            # Laitetaan arvot muuttujaan
            data[parts[0]] = values
            
        except ValueError:
            # Jokin arvoista ei ollut integer
            pass

    # Kun olemme saaneet kaikki 6 riviä napattua, ohjelma mennään ulos silmukasta
    if len(data) >= 6:
        break

# Muunnetaan numpy arrayksi
matrix = np.array([
    data["cp1"],
    data["cp2"],
    data["cp3"],
    data["cp4"],
    data["cp5"],
    data["cp6"]
])

# Plot
fig, ax = plt.subplots()

im = ax.imshow(matrix, cmap="Blues")
labels = ["cp1", "cp2", "cp3", "cp4", "cp5", "cp6"]

ax.set_xticks(range(6))
ax.set_yticks(range(6))

ax.set_xticklabels(labels)
ax.set_yticklabels(labels)

ax.set_xlabel("Predicted")
ax.set_ylabel("Actual")
ax.set_title("Confusion Matrix")

for row in range(6):
    for col in range(6):
        ax.text(
            col,
            row,
            matrix[row, col],
            ha="center",
            va="center",
            color="black"
        )

plt.colorbar(im)
plt.tight_layout()
plt.show()
