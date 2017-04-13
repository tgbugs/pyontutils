#lang brag

short-name : base
base : (m-type | e-type) | reps
reps : (m-type | e-type | location | projection | species) more*
more : underscore reps

e-type : init sust
init : INIT
sust : SUST

location : layer | region
layer : LAYER
region : REGION

underscore : UNDERSCORE
m-type : M-TYPE

projection : PROJECTION

species : SPECIES

