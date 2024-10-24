from skimage.feature import graycomatrix, graycoprops
import numpy as np

class Texture:

    def __init__(self, image):
        self.image = image
        self.mask_array = self.image.astype(np.uint8)
    
    def calculateContrastGlcm(self):
        max_value = np.max(self.mask_array)  
        levels = max_value + 1  
        if self.mask_array.ndim > 2:
            self.mask_array = self.mask_array.reshape(self.mask_array.shape[1], -1)
            
        glcm = graycomatrix(self.mask_array, distances=[1], angles=[0], levels=levels, symmetric=True, normed=True)
        return graycoprops(glcm, 'contrast')
    
    def calculateHomogeneityGlcm(self):
        max_value = np.max(self.mask_array)  
        levels = max_value + 1  
        if self.mask_array.ndim > 2:
            self.mask_array = self.mask_array.reshape(self.mask_array.shape[1], -1)
        glcm = graycomatrix(self.mask_array, distances=[1], angles=[0], levels=levels, symmetric=True, normed=True)
        return graycoprops(glcm, 'homogeneity')
    
    def calculateEntropyGlcm(self):
        max_value = np.max(self.mask_array)  
        levels = max_value + 1  
        if self.mask_array.ndim > 2:
            self.mask_array = self.mask_array.reshape(self.mask_array.shape[1], -1)
        glcm = graycomatrix(self.mask_array, distances=[1], angles=[0], levels=levels, symmetric=True, normed=True)
        glcm_normalized = glcm / np.sum(glcm)

        entropy = -np.sum(glcm_normalized * np.log2(glcm_normalized + 1e-10))  
        return entropy
    
    def calculateCorrelationGlcm(self):
        max_value = np.max(self.mask_array)  
        levels = max_value + 1  
        if self.mask_array.ndim > 2:
            self.mask_array = self.mask_array.reshape(self.mask_array.shape[1], -1)
        glcm = graycomatrix(self.mask_array, distances=[1], angles=[0], levels=levels, symmetric=True, normed=True)
        return  graycoprops(glcm, 'correlation')
    
    def calculateDissimilarityGlcm(self):
        max_value = np.max(self.mask_array) 
        levels = max_value + 1  
        if self.mask_array.ndim > 2:
            self.mask_array = self.mask_array.reshape(self.mask_array.shape[1], -1)
        glcm = graycomatrix(self.mask_array, distances=[1], angles=[0], levels=levels, symmetric=True, normed=True)
        return  graycoprops(glcm, 'dissimilarity')

    def calculateVarianceGlcm(self):
        max_value = np.max(self.mask_array)  
        levels = max_value + 1  
        if self.mask_array.ndim > 2:
            self.mask_array = self.mask_array.reshape(self.mask_array.shape[1], -1)
        glcm = graycomatrix(self.mask_array, distances=[1], angles=[0], levels=levels, symmetric=True, normed=True)
        return  np.var(glcm)
    
    def calculateEnergyGlcm(self):
        max_value = np.max(self.mask_array)  
        levels = max_value + 1  
        if self.mask_array.ndim > 2:
            self.mask_array = self.mask_array.reshape(self.mask_array.shape[1], -1)
        glcm = graycomatrix(self.mask_array, distances=[1], angles=[0], levels=levels, symmetric=True, normed=True)
        return  graycoprops(glcm, 'energy')
    
    def calculateMeanGlcm(self):
        max_value = np.max(self.mask_array)  
        levels = max_value + 1  
        if self.mask_array.ndim > 2:
            self.mask_array = self.mask_array.reshape(self.mask_array.shape[1], -1)
        glcm = graycomatrix(self.mask_array, distances=[1], angles=[0], levels=levels, symmetric=True, normed=True)
        return  np.mean(glcm)