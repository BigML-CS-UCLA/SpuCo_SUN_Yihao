from copy import deepcopy
from typing import Dict, List, Tuple, Any, Optional
import numpy as np 
from enum import Enum 
# FIXME: What if there are more than two groups in inferred group partition, but it is still not class-wise

class GroupEvalSupportedMethod(Enum):
    JTT = "jtt"
    SPARE = "spare"
    EIIL = "eiil"
    
class GroupEvaluator:
    def __init__(
        self,
        method: GroupEvalSupportedMethod,
        inferred_group_partition: Dict[Tuple[int, int], List[int]],
        true_group_partition: Dict[Tuple[int, int], List[int]],
        num_classes: int,
        verbose: bool = False
    ):      

        self.num_classes = num_classes
        self.verbose = verbose
        
        if self.verbose:
            print("Merging true group partition into majority / minority groups only")
        
        if self.verbose:
            print("Processing group partition to get class partition")
            
        # Get all keys corresponding to a class        
        class_wise_keys = {}
        for key in true_group_partition.keys():
            if key[0] in class_wise_keys:
                class_wise_keys[key[0]].append(key)
            else:
                class_wise_keys[key[0]] = [key]
                
        # Merge lists for keys corresponding to 1 class
        self.class_wise_partition = {}
        for class_id in class_wise_keys.keys():
            self.class_wise_partition[class_id] = []
            for key in class_wise_keys[class_id]:
                self.class_wise_partition[class_id].extend(true_group_partition[key])
        
        # Merging true group partition into min and maj
        self.true_group_partition = {}
        
        # Single spurious only
        if type(list(true_group_partition.keys())[0][1]) == int:   
            for class_id in self.class_wise_partition.keys():
                self.true_group_partition[(class_id, "majority")] = []
                self.true_group_partition[(class_id, "minority")] = [] 
            for key in true_group_partition.keys():
                if key[0] == key[1]:
                    self.true_group_partition[(key[0], "majority")].extend(true_group_partition[key])
                else:
                    self.true_group_partition[(key[0], "minority")].extend(true_group_partition[key])
        else:
            raise NotImplementedError("Not supporting multiple spurious currently")
        self.true_group_labels = GroupEvaluator.invert_group_partition(self.true_group_partition)
           
        if self.verbose:
            print("Merging inferred group partition into majority / minority groups only for {method.value}")
        if method == GroupEvalSupportedMethod.JTT:
            # Error set is referenced as (0,1) and corresponds to minority
            # Partition to create class-wise majority, minority
            self.inferred_group_partition = {}
            for class_id in self.class_wise_partition.keys():
                self.inferred_group_partition[(class_id, "majority")] = np.intersect1d(self.class_wise_partition[class_id], inferred_group_partition[(0,0)])
                self.inferred_group_partition[(class_id, "minority")] = np.intersect1d(self.class_wise_partition[class_id], inferred_group_partition[(0,1)])
        elif method == GroupEvalSupportedMethod.EIIL:
            # Guess 1 for majority
            self.inferred_group_partition = {}
            for class_id in self.class_wise_partition.keys():
                self.inferred_group_partition[(class_id, "majority")] = np.intersect1d(self.class_wise_partition[class_id], inferred_group_partition[(0,0)])
                self.inferred_group_partition[(class_id, "minority")] = np.intersect1d(self.class_wise_partition[class_id], inferred_group_partition[(0,1)])
            inferred_group_partition1 = deepcopy(self.inferred_group_partition)
            self.inferred_group_labels = GroupEvaluator.invert_group_partition(self.inferred_group_partition)
            acc1 = self.evaluate_accuracy()
            
            # Guess 2 for majority
            self.inferred_group_partition = {}
            for class_id in self.class_wise_partition.keys():
                self.inferred_group_partition[(class_id, "majority")] = np.intersect1d(self.class_wise_partition[class_id], inferred_group_partition[(0,1)])
                self.inferred_group_partition[(class_id, "minority")] = np.intersect1d(self.class_wise_partition[class_id], inferred_group_partition[(0,0)])
            inferred_group_partition2 = deepcopy(self.inferred_group_partition)
            self.inferred_group_labels = GroupEvaluator.invert_group_partition(self.inferred_group_partition)
            acc2 = self.evaluate_accuracy()
            
            if acc1 > acc2:
                self.inferred_group_partition = inferred_group_partition1
            else:
                self.inferred_group_partition = inferred_group_partition2
        else:
            raise NotImplementedError("Unsupported method")
        
                
        if self.verbose:
            print("Inverting inferred group partition")
        self.inferred_group_labels = GroupEvaluator.invert_group_partition(self.inferred_group_partition)
    
    @staticmethod
    def invert_group_partition(group_partition: Dict):
        group_labels_dict = {}
        for key in group_partition.keys():
            for i in group_partition[key]:
                group_labels_dict[i] = key
                
        group_labels = []
        for i in range(len(group_labels_dict)):
            group_labels.append(group_labels_dict[i])
        
        return group_labels
    
    def evaluate_accuracy(self):
        correct = 0
        total = 0
        
        for inferred, true in zip(self.inferred_group_labels, self.true_group_labels):
            if inferred == true:
                correct += 1
            total += 1
        
        return correct / total
    
    def evaluate_precision(self):
        precisions = []
        
        for class_num in range(self.num_classes):
            true_pos = 0
            min_group = (class_num, "min")
            for i in self.inferred_group_partition[min_group]:
                if self.true_group_labels[i] == min_group:
                    true_pos += 1
            precisions.append(true_pos / len(self.inferred_group_partition[min_group]))
        
        return np.mean(precisions), np.min(precisions)
    
    def evaluate_recall(self):
        recall = []
        
        for class_num in range(self.num_classes):
            true_pos = 0
            min_group = (class_num, "min")
            for i in self.inferred_group_partition[min_group]:
                if self.true_group_labels[i] == min_group:
                    true_pos += 1
            recall.append(true_pos / len(self.true_group_partition[min_group]))
        
        return np.mean(recall), np.min(recall)    

   
                
        
        
        