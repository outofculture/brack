def process_data(data_list,filter_func,transform_func):
    filtered_data=[]
    for item in data_list:
        if filter_func(item):
            transformed=transform_func(item)
            filtered_data.append(transformed)
    return filtered_data

class DataProcessor:
    def __init__(self,config):
        self.config=config
        self.results=[]
    
    def process(self,data):
        for item in data:
            if self.validate(item):
                processed=self.transform(item)
                self.results.append(processed)
