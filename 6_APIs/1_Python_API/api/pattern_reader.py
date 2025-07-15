import json

class PatternReader:
    """
    A class for reading and managing pattern parameters from a JSON file.

    This class loads execution and simulation parameters from a JSON file 
    along with multiple pattern data entries. It provides functionality to:
    - Load a JSON file
    - Retrieve stored parameters
    - Iterate through available patterns in a cyclic manner
    - Reset iteration index to start from the first pattern
    """

    def __init__(self):
        """
        Initialize the PatternReader object.

        Attributes:
            parameters (dict): Dictionary to store 'Execution', 'Simulation' parameters.
            patterns (list): A list that holds pattern data from the JSON file.
            index (int): An internal index to keep track of the current pattern in `patterns`.
        """
        self.patterns = []
        self.index = 0

    def load_file(self, file_path):
        """
        Load the JSON data from the given file and populate the parameters and patterns.

        Args:
            file_path (str): The path to the JSON file containing pattern data.
                The JSON file should contain keys for 'Execution', 'Simulation' and 'Pattern_Data'.

        Raises:
            FileNotFoundError: If the specified file path does not exist.
            JSONDecodeError: If the file contains invalid JSON.
        """
        with open(file_path, 'r') as file:
            data = json.load(file)
        # Load patterns
        self.patterns = data["Pattern_Data"]
        # Initialize index
        self.index = 0
    
    def reset_pattern_index(self):
        """
        Reset the pattern index to the first pattern.

        This sets `self.index` to 0, ensuring that subsequent calls
        to `next_pattern()` return patterns starting from the beginning
        of the list.
        """
        self.index = 0

    def next_pattern(self):
        """
        Retrieve the next pattern frame with ON and OFF times.

        This method cycles through patterns in `self.patterns`. Once it 
        reaches the end, it loops back to the beginning (cyclic iteration).

        Returns:
            dict: A dictionary with keys:
                - 'pattern': The pattern identifier or data.
                - 'on_time': The ON delay from the pattern.
                - 'off_time': The OFF delay from the pattern.
                - 'frequency': The frequency of the pattern.
                - 'stim_mode': The stimulation mode - Anodic ot Cathodic.

        Raises:
            ValueError: If no pattern data has been loaded prior to calling this method.
        """
        if not self.patterns:
            raise ValueError("Pattern data not loaded.")
        
        # Get the current pattern
        pattern_group = self.patterns[self.index]
        pattern_info = pattern_group[0]
        
        # Increment the index and reset if needed
        self.index = (self.index + 1) % len(self.patterns)
        
        return {
            "pattern":   pattern_info["pattern"],
            "on_time":   pattern_info["delay"]["ON"],
            "off_time":  pattern_info["delay"]["OFF"],
            "frequency": pattern_info["params"]["frequency"],
            "stim_mode":  pattern_info["params"]["stim_mode"]
        }

if __name__ == "__main__":
    # Example Usage
    file_path = './example_patterns/test_pattern.json'  # Replace with your actual file path
    pattern_reader = PatternReader()
    pattern_reader.load_file(file_path)

    # Get parameters
    pattern_reader.reset_pattern_index()

    # Fetch patterns
    for _ in range(10):  # Fetching first 10 patterns as an example
        pattern = pattern_reader.next_pattern()
        print("Pattern Frame:", pattern)