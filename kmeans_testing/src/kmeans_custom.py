'''
Ohjelma toteuttaa K-means clustering algoritmin. Pääpiirteittäin se
tekee näin:

Vaihe 1:
    Valitaan kuinka monta klusteria (cluster, "k") datasta halutaan tunnistaa.
    Tässä ohjelmassa tämä arvo on 6, ja se perustuu käyttämiemme suuntien
    määrään, joita projektissamme on 6 kappaletta. Haluamme siis jaotella
    datamme 6 eri klusteriin (suuntaan).
Vaihe 2:
    Valitaan satunnaiset "k" kappaletta klustereiden keskipisteitä (centroid)
    näytteistä (X).
Vaihe 3:
    Mitataan datapisteen eli näytteen etäisyys jokaiseen klusteriin. 
    Tämä tapahtuu mittaamalla datapisteen euklidinen etäisyys klustereiden
    centroideihin. Datapiste lokeroidaan siihen klusteriin, johon sillä on
    lyhin etäisyys. Tämä tehdään jokaiselle datapisteelle niin, että lopulta
    kaikki datapisteet kuuluvat johonkin klusteriin.
Vaihe 4:
    Lasketaan jokaisen klusterin datapisteiden keskiarvo. Tästä keskiarvosta
    tulee klusterin uusi keskipiste eli centroid.
Vaihe 5:
    Toistetaan vaiheita 3-4 kunnes klustereiden centroidit eivät enää muutu.
    Tällöin olemme saavuttaneet konvergenssin ("convergence").
Vaihe 6:
    Arvioidaan (assess) klusteroinnin laatua laskemalla klustereiden variaatio.
    Ensin lasketaan klustereiden sisältämien datapisteiden etäisyydet klustereiden
    keskipisteisiin. Etäisyydet korotetaan toiseen potenssiin. Tulokset summataan
    yhteen. Mitä alhaisempi tulos on, sitä paremmin klusterointi onnistui.
Vaihe 7:
    Toistetaan vaiheita 2-6 kunnes olemme tyytyväisiä. Jokaisella kierroksella
    laskettua variaatiota verrataan aiempaan kierrokseen, ja mikäli se on alhaisempi,
    nykyisen kierroksen klusteroinnista tulee uusi paras tulos. 
'''

import numpy as np
import matplotlib.pyplot as plt
from numpy import genfromtxt

# Plotting enabled/disabled
plot: bool = False

# Thanks to broadcasting, this will expand into sqrt((x2 - x1)^2 + (y2 - y1)^2) + ... + (n2 -n1)^2)
# In other words, it will work with any array dimensions
def euclidean_distance(point_1, point_2):
    return np.sqrt(np.sum((point_1 - point_2)**2))

# Assigns all samples to the closest centroid. Clustered samples are stored in clusters array.
def assign_to_clusters(X, clusters, centroids):
    num_samples = X.shape[0]
    num_clusters = len(clusters)
    distances = np.empty((num_samples, num_clusters), dtype=np.float32)
    
    for idx in range(num_samples):
        for idk in range(num_clusters):
            distance = euclidean_distance(X[idx], centroids[idk]) 
            distances[idx][idk] = distance

        # Assign the datapoint to the nearest cluster.
        closest_centroid_index = np.argmin(distances[idx])
        clusters[closest_centroid_index].append(X[idx])

# Calculates the mean of each cluster. The mean becomes the new cluster centroid.
def update_centroids(clusters, centroids):
    num_clusters = len(clusters)
    for i in range(num_clusters):
        if len(clusters[i]) == 0:
            continue
        centroids[i] = np.mean(clusters[i], axis=0)

# Calculates the distances the points are from the centroid, raises them
# to the 2nd power and sums them all up. Higher values = bad,
# lower values = good
def assess_clusters(clusters, centroids):
    sum = 0.0
    for i in range(len(clusters)):
        if len(clusters[i]) == 0:
            continue
        for j in range(len(clusters[i])):
            distance = euclidean_distance(clusters[i][j], centroids[i])
            sum += distance**2
    return sum

# Plot clustered data + centroids
def plot_clustered(clusters, centroids, title):
    fig = plt.figure(figsize=(8,6))
    ax = fig.add_subplot(111, projection='3d')

    # Represent centroids as a '*' symbol with a circle around it.
    ax.scatter3D(centroids[:,0], centroids[:,1], centroids[:,2], marker='o', s=300, facecolors='none', edgecolors='black', linewidths=1)
    ax.scatter3D(centroids[:,0],   centroids[:,1],   centroids[:,2],   color='red', marker='*')

    colors = ['blue', 'green', 'yellow', 'pink', 'orange', 'cyan', 'brown', 'black', 'purple', 'olive', 'gray']
    for i in range(len(clusters)):
        if len(clusters[i]) == 0:
            continue
        ax.scatter3D(clusters[i][:,0], clusters[i][:,1], clusters[i][:,2], color=colors[i % len(colors)], marker='o', label=f'cluster {i}')

        # Draw a line going from cluster datapoints to cluster centroid
        for point in clusters[i]:
            ax.plot([centroids[i][0], point[0]],[centroids[i][1], point[1]],[centroids[i][2], point[2]],color='gray',alpha=0.5,linewidth=0.5)

    ax.legend(loc='lower right')
    ax.set_xlabel('X Axis')
    ax.set_ylabel('Y Axis')
    ax.set_zlabel('Z Axis')
    ax.set_title(title)
    plt.show()

# Plot raw data + centroids
def plot_raw(X, centroids):
    fig = plt.figure(figsize=(8,6))
    ax = fig.add_subplot(111, projection='3d')
    
    # Centroids are a '*' symbol with a circle around them.
    ax.scatter3D(centroids[:,0], centroids[:,1], centroids[:,2], marker='o', s=300, facecolors='none', edgecolors='black', linewidths=1)
    ax.scatter3D(centroids[:,0],   centroids[:,1],   centroids[:,2],   color='red', marker='*')

    # Datapoints
    ax.scatter3D(X[:,0], X[:,1], X[:,2], color='blue', marker='o', label='datapoints')
        
    ax.set_xlabel('X Axis')
    ax.set_ylabel('Y Axis')
    ax.set_zlabel('Z Axis')
    ax.set_title('Data + initial centroids')
    plt.show()

# Select the number of clusters you want to identify
k = 6

# Read data
X = genfromtxt('data_0_S160000_1795623698.csv', delimiter=',')
# X = genfromtxt('simple_demo_data.csv', delimiter=',')

# Will store the best cluster set
final_clusters = []
final_centroids = []

# How many times we repeat the entire thing with new starting centroids
# The clustering with least amount of variance of all clusters will win
max_outer_iterations = 5
smallest_error = float("inf")
for i in range(max_outer_iterations):    
    print(f"Running ({i+1}/{max_outer_iterations})")
    
    # Randomly select initial centroids from the datapoints
    indices = np.random.choice(len(X), k, replace=False)
    centroids = X[indices].copy().astype(float)
    
    print("Initial centroids:")
    for c in centroids:
        print(c)

    # Plot raw data + centroids
    if plot:
        plot_raw(X, centroids)

    # How many times we adjust the centroids and re-cluster
    max_inner_iterations = 10
    for j in range(max_inner_iterations):
        print(f"Iteration {j+1} (max: {max_inner_iterations})")
        
        # Init clusters array
        clusters =  [[] for _ in range(k)]

        # Assign all samples into clusters.
        assign_to_clusters(X, clusters, centroids)

        print("Cluster sizes:")
        for c in range(len(clusters)):
            print(f"cluster {c}: {len(clusters[c])}")

        # Convert python lists to numpy arrays so that we can use index slicing for plotting
        clusters = [np.array(cluster) for cluster in clusters]
 
        # Plot clustered data + centroids
        if plot:
            plot_clustered(clusters, centroids, 'Clustered Data + centroids')

        # Save the old centroids for comparison
        old_centroids = centroids.copy()

        # Update centroids
        update_centroids(clusters, centroids)

        # Plot clustered data + centroids
        if plot:
            plot_clustered(clusters, centroids, 'Clustered Data + centroids')

        # Compare to previous centroids. If they are similar then exit loop
        if np.allclose(old_centroids, centroids):
            print("centroids converged, breaking...")
            break
    
    # Assess the quality of the clustering
    iteration_error = assess_clusters(clusters, centroids)
    print(f"Iteration error was {iteration_error}")
    
    if iteration_error < smallest_error:
        final_clusters = clusters.copy()
        final_centroids = centroids.copy()
        smallest_error = iteration_error

if plot:
    plot_clustered(final_clusters, final_centroids, 'Final clusters + centroids')

# Write resulting centroids into a file
filename = f"keskipisteet.h"
content = f"int CP[{k}][3] = {{\n"

for c in final_centroids:
    content += f"{{{int(c[0])}, {int(c[1])}, {int(c[2])}}},\n"
content += f"}};"

if content:
    print("writing centroids to file:", final_centroids)
    with open(filename, "w", encoding="utf-8") as tiedosto:
        tiedosto.write(content)
