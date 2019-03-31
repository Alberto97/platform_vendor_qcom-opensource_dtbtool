Python QCDT DTB Tool
========================

A completely backwards compatible python rewritten qcom dtbtool.

The following options are supported:
  
| **Short Argument** | **Long Argument** | **Description**                                                                   |
|:------------------:|:------------------|:----------------------------------------------------------------------------------|
|                    |                   | Parameter without arguments is input directory. Subfolders will be picked as well |
| -o                 | --output-file     | Output dtb image                                                                  |
| -p                 | --dtc-path        | Path to dtc binary                                                                |
| -s                 | --page-size       | Page Size in bytes. Default value is 2048                                         |
| -d                 | --dt-tag          | Custom QCDT_DT_TAG tag. Default is: "qcom,msm-id = <"                             |
| -2                 | --force-v2        | Force generating v2 output DTB                                                    |
| -3                 | --force-v3        | Force generating v3 output DTB                                                    |

It will generate a dtb image with the following structure:

## QCDT DTB Structure

| **Structure**       | **Size**                          | **Notes**                                     |
|:-------------------:|:----------------------------------|:----------------------------------------------|
| Header              | 12B                               | See header structure                          |
| Chip Index Table #1 | variable                          | See Chip Index Table structure                |
| ...                 |                                   |                                               |
| Chip Index Table #Z | variable                          | See Chip Index Table structure                |
| 0 ("zero")          | uint32                            | end of list delimiter                         |
| padding             | variable                          | length for next DTB to start on page boundary |
| DTB #1              | variable                          |                                               |
| padding             | variable                          | length for next DTB to start on page boundary |
| DTB #2              | variable                          |                                               |
| ...                 |                                   |                                               |
| DTB #Z              | variable                          |                                               |

### Header Structure
  
| **Structure** | **Size** | **Notes**             |
|:-------------:|:---------|:----------------------|
| Magic         | 4B       | QCDT                  |
| QCDT Version  | uint32   | e.g. 3                |
| DTB Entries   | uint32   | number of DTB entries |

### Chip Index Table Structure

| **Structure** | **Size** | **Notes**                                        | **QCDT Version** |
|:-------------:|:---------|:-------------------------------------------------|:----------------:|
| Chipset       | uint32   | e.g. ID for chipset                              |                  |
| Platform      | uint32   | e.g. ID for MSM8974                              |                  |
| Subtype       | uint32   | e.g. ID for subtype                              | v2/v3 only       |
| Soc Revision  | uint32   | e.g. MSM8974 v2                                  |                  |
| PMIC0         | uint32   | first smallest SID of existing pmic              | v3 only          |
| PMIC1         | uint32   | secondary smallest SID of existing pmic          | v3 only          |
| PMIC2         | uint32   | third smallest SID of existing pmic              | v3 only          |
| PMIC3         | uint32   | fourth smallest SID of existing pmic             | v3 only          |
| DTB Offset    | uint32   | byte offset from start/before MAGIC to DTB entry |                  |
| DTB Size      | uint32   | size in bytes of DTB blob                        |                  |

