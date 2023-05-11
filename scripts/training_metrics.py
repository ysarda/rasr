"""
Training evaluation ver 1.0
as of March 23, 2022

Script used for the evalution of Detecto NN

@author: Carson Lansdowne
"""

from detecto.core import Dataset, Model
import matplotlib.pyplot as plt

from glob import glob
import xml.etree.ElementTree as ET
import pandas as pd


def my_xml_to_csv(xml_folder, output_file=None):
    """Converts a folder of XML label files into a pandas DataFrame and/or
    CSV file, which can then be used to create a :class:`detecto.core.Dataset`
    object. Each XML file should correspond to an image and contain the image
    name, image size, image_id and the names and bounding boxes of the objects in the
    image, if any. Extraneous data in the XML files will simply be ignored.
    See :download:`here <../_static/example.xml>` for an example XML file.
    For an image labeling tool that produces XML files in this format,
    see `LabelImg <https://github.com/tzutalin/labelImg>`_.
    :param xml_folder: The path to the folder containing the XML files.
    :type xml_folder: str
    :param output_file: (Optional) If given, saves a CSV file containing
        the XML data in the file output_file. If None, does not save to
        any file. Defaults to None.
    :type output_file: str or None
    :return: A pandas DataFrame containing the XML data.
    :rtype: pandas.DataFrame
    **Example**::
        >>> from detecto.utils import xml_to_csv
        >>> # Saves data to a file called labels.csv
        >>> xml_to_csv('xml_labels/', 'labels.csv')
        >>> # Returns a pandas DataFrame of the data
        >>> df = xml_to_csv('xml_labels/')
    """

    xml_list = []
    image_id = 0
    # Loop through every XML file
    for xml_file in glob(xml_folder + "/*.xml"):
        tree = ET.parse(xml_file)
        root = tree.getroot()

        filename = root.find("filename").text
        size = root.find("size")
        width = int(size.find("width").text)
        height = int(size.find("height").text)

        if root.find("object"):
            # Each object represents each actual image label
            for member in root.findall("object"):
                box = member.find("bndbox")
                label = member.find("name").text

                # Add image file name, image size, label, and box coordinates to CSV file
                row = (
                    filename,
                    width,
                    height,
                    label,
                    int(float(box.find("xmin").text)),
                    int(float(box.find("ymin").text)),
                    int(float(box.find("xmax").text)),
                    int(float(box.find("ymax").text)),
                    image_id,
                )
                xml_list.append(row)
        else:
            row = (filename, width, height, "none", 0, 0, 0, 0, image_id)
            xml_list.append(row)

        image_id += 1

    # Save as a CSV file
    column_names = [
        "filename",
        "width",
        "height",
        "class",
        "xmin",
        "ymin",
        "xmax",
        "ymax",
        "image_id",
    ]
    xml_df = pd.DataFrame(xml_list, columns=column_names)

    if output_file is not None:
        xml_df.to_csv(output_file, index=None)

    return xml_df


# my_xml_to_csv('training/experiments/2500/w_null/validation/', 'training/experiments//2500/w_null/vlabel.csv')
# df
# my_xml_to_csv("training/experiments//2500/w_null/train/", 'training/experiments/o/2500/w_null/tlabel.csv')
# df2

# set epoch count


e = 15

tdataset_null = Dataset(
    "training/experiments/2500/w_null/tlabel.csv",
    "training/experiments/2500/w_null/train/",
)  # Training dataset
vdataset_null = Dataset(
    "training/experiments/2500/w_null/vlabel.csv",
    "training/experiments/2500/w_null/validation/",
)  # Evaluation dataset

print(len(tdataset_null))
print(len(vdataset_null))

model_null = Model(["fall", "none"])

# Keep the learning rate low, otherwise the loss will be too high
loss_null = model_null.fit(
    tdataset_null,
    vdataset_null,
    epochs=e,
    learning_rate=0.001,
    gamma=0.2,
    lr_step_size=5,
    verbose=True,
)

plt.plot(loss_null)
plt.xlabel("Epoch")
plt.ylabel("Loss (w/ null)")
plt.show()
model_null.save("RASRmodl_null.pth")
