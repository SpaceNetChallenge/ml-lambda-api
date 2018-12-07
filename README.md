# ml-lambda-tiler

#### AWS Lambda + rio-tiler + STAC to provide Machine Learning Results to HOTOSM Tasking Manager

# Info


---

# Installation

##### Requirement
  - AWS Account
  - Docker
  - node + npm


#### Create the package

```bash
# Build Amazon linux AMI docker container + Install Python modules + create package
git clone https://github.com/SpaceNetChallenge/ml-lambda-api.git
cd ml-lambda-all
make all
```

#### Deploy to AWS

```bash
#configure serverless (https://serverless.com/framework/docs/providers/aws/guide/credentials/)
npm install
sls deploy
```

# Endpoint

## STAC API


### /stac/bounds

*Inputs:*
- url: any valid url

*example:*
```
$ curl {you-endpoint}/stac/bounds?url=https://any-stac-item.json

  {"url": "https://any-file.on/the-internet.tif", "bounds": [90.47546096087822, 23.803014490532913, 90.48441996322644, 23.80577697976369]}
```

### /stac/tile/z/x/y.png
*Inputs:*
- url: any valid url
- asset_key: asset key from STAC_ITEM : default = segmentation_mask
*Options:*
- rgb: select bands indexes to return (e.g: (1,2,3), (4,1,2))
- nodata: nodata value to create mask

*example:*
```
$ curl {you-endpoint}/stac/tiles/7/10/10.png?url=https://any-stac-item.json
```

### /stac/summary/z/x/y.json
*Inputs:*
- url: any valid url
- asset_key: asset key from STAC_ITEM : default = segmentation_mask

*Outputs:*
- pixel_count:  Number of pixels of value out of 255
- object_count: Number of objects after polygonization
- sqkm:   sqkm of Object  

*example:*
```
$ curl {you-endpoint}/stac/tiles/7/10/10.png?url=https://any-stac-item.json&asset_key=segmentation_mask
  { 
  "pixel_count": 555,
  "object_count": 1000,
  "sqkm": 1234
  }
```


## COG API

### /bounds

*Inputs:*
- url: any valid url

*example:*
```
$ curl {you-endpoint}/bounds?url=https://any-file.on/the-internet.tif

  {"url": "https://any-file.on/the-internet.tif", "bounds": [90.47546096087822, 23.803014490532913, 90.48441996322644, 23.80577697976369]}
```

### /tiles/z/x/y.png

*Inputs:*
- url: any valid url

*Options:*
- rgb: select bands indexes to return (e.g: (1,2,3), (4,1,2))
- nodata: nodata value to create mask

*example:*
```
$ curl {you-endpoint}/tiles/7/10/10.png?url=https://any-file.on/the-internet.tif

```
