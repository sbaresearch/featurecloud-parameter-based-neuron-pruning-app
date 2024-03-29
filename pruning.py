from onnx import numpy_helper
import numpy as np


def modify_and_update_network(model, percentage_to_prune):
    for initializer in model.graph.initializer:
        # Check if the data is in raw format
        if initializer.HasField('raw_data'):
            weight_data = numpy_helper.to_array(initializer)
        else:
            # Assume the data is in float format
            weight_data = np.array(initializer.float_data).reshape(initializer.dims)

        if percentage_to_prune > 0:
            # Flatten the weight data for easier processing
            #flattened_weights = weight_data.flatten()
            # Convert the ONNX tensor to a numpy array
            # Set the given % of lowest values to zero
            modified_weight_data = set_lowest_values_to_zero(weight_data, percentage_to_prune)
            # Create a new initializer with the modified array
            new_initializer = numpy_helper.from_array(modified_weight_data, name=initializer.name)
            # Replace the old initializer with the modified one
            initializer.CopyFrom(new_initializer)

            # Reshape the modified weights to the original shape
            modified_weights = np.array(modified_weight_data).reshape(weight_data.shape)

            # Convert the modified weights to the serialized binary format
            serialized_data = modified_weights.astype(np.float32).tobytes()

            # Clear the existing data fields
            initializer.ClearField('float_data')

            # Update the raw_data field of the initializer
            initializer.raw_data = serialized_data

    return model

# Function to prune the connections from the network
def prune_connections(model, percentage_to_prune):
    modified_model = modify_and_update_network(model, percentage_to_prune)
    return modified_model

def set_lowest_values_to_zero(param_array, percentage):
    #Set the percentage of lowest absolute values in the array to zero.
    # Flatten the array to work with it as a 1D array
    flat_array = param_array.flatten()
    # Calculate the number of values to set to zero
    num_values_to_zero = int(len(flat_array) * percentage)
    # Find the threshold below which values will be set to zero
    threshold = np.partition(abs(flat_array), num_values_to_zero)[num_values_to_zero]
    # Set values below the threshold to zero
    flat_array[abs(flat_array) < threshold] = 0
    # Reshape the array back to its original shape
    return flat_array.reshape(param_array.shape)

def compare_original_to_modified(original_model, modified_model):
    # Load the original and modified ONNX models

    # Extract initializers (parameters) from both models
    original_initializers = {init.name: numpy_helper.to_array(init) for init in original_model.graph.initializer}
    modified_initializers = {init.name: numpy_helper.to_array(init) for init in modified_model.graph.initializer}

    # Check if the initializers in both models have the same structure
    same_structure = True
    if set(original_initializers.keys()) != set(modified_initializers.keys()):
        same_structure = False
    else:
        for key in original_initializers:
            if original_initializers[key].shape != modified_initializers[key].shape:
                same_structure = False
                break

    return same_structure


def compare_graph_structure(original_model, modified_model):
    # Check if the nodes in both graphs have the same structure
    if len(original_model.graph.node) != len(modified_model.graph.node):
        return False

    for original_node, modified_node in zip(original_model.graph.node, modified_model.graph.node):
        if original_node.op_type != modified_node.op_type:
            return False
        if original_node.input != modified_node.input:
            return False
        if original_node.output != modified_node.output:
            return False

    return True
