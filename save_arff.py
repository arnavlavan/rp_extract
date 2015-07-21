# 20.07.2015 by Thomas Lidy
# based on arff writing code by Alexander Schindler

import os
import pandas as pd
from rp_extract_files import read_feature_files



def save_arff(filename,dataframe,relation_name=None):
    
    if relation_name is None:
        relation_name = filename
    
    out_file = open(filename, 'w')
    
    out_file.write("@Relation {0}\n".format(relation_name))
    
    for column in dataframe:
        if column == "ID": 
            out_file.write("@Attribute ID string\n")
        elif column == "class":
            class_list = dataframe["class"].unique()
            out_file.write("@Attribute class {{{0}}}\n".format(",".join(class_list)))   
        else:
            # assume all other columns are numeric
            out_file.write("@Attribute {0} numeric\n".format(column))
    
    # now for the feature data
    out_file.write("\n@Data\n")
    dataframe.to_csv(out_file, header=None, index=None)
    
    # NumPy variant:
    #np.savetxt(out_file, a, delimiter=",")
    
    out_file.close()
    
    

# converts np.array + extra ids and/or classes to Pandas dataframe
# ids (e.g. audio filenames) and classes can be provided optionally as list (will be excluded if omitted)
# feature attribute labels also optionally as a list (will be generated if omitted)

def to_dataframe(feature_data, attribute_labels=None, ids=None, classes=None):

    if attribute_labels is None:
        attribute_labels = feature_data.dtype.names
        if attribute_labels == None:
            # if nothing is passed and nothing is stored in np array we create the attribute names
            fdim = feature_data.shape[1]
            attribute_labels = [("feat" + str(x)) for x in range(fdim)]
            
    if feature_data.dtype == object: # convert to float for proper PD output to arff
        feature_data = feature_data.astype(float)

    dataframe = pd.DataFrame(feature_data, columns=attribute_labels)
    
    if not ids is None:
        dataframe["ID"] = ids

    if not classes is None:
        dataframe["class"] = pd.Categorical(classes) # classes 
        
    return dataframe




if __name__ == '__main__':


    vec_path = '/data/music/GTZAN/vec'

    filenamestub = 'GTZAN.python'

    feature_types = ['rp','ssd','rh','mvd']


    # READ CSV (all feature types into a dict)
    full_filenamestub = vec_path + os.sep + filenamestub

    ids, features = read_feature_files(full_filenamestub,feature_types)


    for ext in feature_types:

        # ADD CLASS LABEL
        # only works for GTZAN collection: class is first part of filename before '.'
        classes = [x.split('.', 1)[0] for x in ids[ext]]

        # CREATE DATAFRAME
        # with ids
        #df = to_dataframe(features[ext], None, ids[ext], classes)
        # without ids
        df = to_dataframe(features[ext], classes=classes)

        # WRITE ARFF
        out_filename = full_filenamestub + "." + ext + ".arff"
        print "Saving " + out_filename + " ..."
        save_arff(out_filename,df)

    print "Finished."

