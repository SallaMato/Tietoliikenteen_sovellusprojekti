#ifndef CONFUSION_MATRIX_H
#define CONFUSION_MATRIX_H

void printConfusionMatrix(void);
void makeHundredFakeClassifications(void);
void makeOneClassificationAndUpdateConfusionMatrix(int);
void classifyAndUpdateConfusionMatrix(uint8_t*, int);
int calculateDistanceToAllCentrePointsAndSelectWinner(int,int,int);
void resetConfusionMatrix(void);

// Helpers
int euclidean_distance(int x1, int y1, int z1, int x2, int y2, int z2);

#endif
