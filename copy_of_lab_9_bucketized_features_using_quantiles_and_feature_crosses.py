# -*- coding: utf-8 -*-
"""Copy of Lab 9: Bucketized Features Using Quantiles and Feature Crosses.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/11WhV3t7HxxRedCqyKFQT6ccZaISOPo0S

#### Copyright 2017 Google LLC.
"""

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""# Lab 9: Bucketized Features Using Quantiles and Feature Crosses
**Learning Objectives:**
  * Learn to use quantiles to create bucketized features.
  * Learn how to introduce feature crosses.
  * Starting from just having the data loaded, train a linear classifier to predict if an individual's income is at least 50k using numerical features, categorical features, bucketized features, and feature crosses.

### Standard Set-up

We begin with the standard set-up as seen in the last lab again using the census data set.
"""

import math

from IPython import display
from matplotlib import cm
from matplotlib import gridspec
from matplotlib import pyplot as plt
import numpy as np
import pandas as pd
from mpl_toolkits.mplot3d import Axes3D
from sklearn import metrics
import tempfile
import tensorflow as tf
from tensorflow.contrib.learn.python.learn import learn_io, estimator
import urllib

# This line increases the amount of logging when there is an error.  You can
# remove it if you want less logging.
tf.logging.set_verbosity(tf.logging.ERROR)

# Set the output display to have two digits for decimal places, for display
# readability only and limit it to printing 15 rows.
pd.options.display.float_format = '{:.2f}'.format
pd.options.display.max_rows = 15


train_file = tempfile.NamedTemporaryFile()
urllib.urlretrieve("http://mlr.cs.umass.edu/ml/machine-learning-databases/adult/adult.data", train_file.name)

COLUMNS = ["age", "workclass", "sample_weight", "education", "education_num",
           "marital_status", "occupation", "relationship", "race", "gender",
           "capital_gain", "capital_loss", "hours_per_week", "native_country",
           "income_bracket"]
census_df = pd.read_csv(train_file, names=COLUMNS, skipinitialspace=True)

"""### Making Numerical Features Categorical through Bucketization

As we saw in [Lab4 (Using Bucketized Numerical Features)](https://colab.sandbox.google.com/notebook#fileId=/v2/external/notebooks/intro_to_ml_semester_course/Lab_4__Using_a_Bucketized_Numerical_Feature.ipynb), often the relationship between a numerical feature and the label is not linear. As an example relevant to this data set, a person's income may grow with age in the early stage of one's career, then the growth may slow at some point, and finally the income decreases after retirement. If we want to learn the fine-grained correlation between income and each age group separately, we can leverage bucketization (also known as binning).  **Bucketization** is a process of partitioning the entire range of a numerical feature into bins/buckets, and then converting the original numerical feature into a set of categorical features with one feature correpsonding to each bucket (with a value of 1 when the numerical feature falls in the range of the bucket, and 0 otherwise). However, in general, it is not feasible to hand pick boundaries as we did for compression ratio in Lab 4.


### Computing Quantile Boundaries ###

A good general approach is to bucketize features into groups so that there are roughly the same number of examples falling into each group.  Such groups are called ***quantiles*** and can be computed very simply as illustrated below in `get_quantile_based_boundaries`.
"""

def get_quantile_based_boundaries(feature_values, num_buckets):
  boundaries = np.arange(1.0, num_buckets) / num_buckets
  quantiles = feature_values.quantile(boundaries)
  return [q for q in quantiles]

"""Let's try it out on `age` with 5 quantiles. We use plot to visualize the boundaries on a histogram. So the bins defined for `age` on this data are $\le$25, 26-32, 33-40, 41-49, and $\ge$50."""

histogram = census_df["age"].hist(bins=50)
boundaries = get_quantile_based_boundaries(census_df["age"], 5)
print "boundaries are:", boundaries
for x in boundaries:
  plt.axvline(x, color='g')

"""### Feature Crosses

As we discussd in the slides, another very powerful way to capture non-linear behavior in a linear model is through introducing feature crosses. Any combination of categorical features and bucketized features (which are a form of categorical feature) can be combined in a **feature cross**.  When this is done there will be a new categorical featuers introduced for each possible value for all the features in the cross.  Thus if a feature with `n1` values is crossed with a feature with `n2` values then there will be `n1 * n2` features for the cross.

Here is a sample of creating a cross between `gender` and `age_buckets`.
```
   gender_x_age_buckets = tf.contrib.layers.crossed_column(
      [gender, age_buckets], hash_bucket_size=1000
```

If we had defined 5 age buckets as above, then this crossed column would introduce 10 Boolean features: one for males in each of the 5 age buckets listed above, and one for females in each of the 5 age buckets.

## Task 1 - Train a Linear Classifier with Bucketized Features and Feature Crosses (5 points)

For this lab, you are going to train a model to improve upon what you did in Lab 8 by introducing bucketized features and feature crosses.  You should introduce at least two bucketized features and at two feature crosses.

Unlike in past labs, we are not providing any code other than what is provided above to load the data into Pandas, and compute quantile boundaries.  Just to be sure it is clear how to introduce a `bucketized_colum` and a`crossed_column` column below is a starting point for `construct_feature_column`.  Copy any of pieces of code that you'd like to use from Lab 8.

**WARNING: As discussed in the slides, because the log loss has a gradient that goes to infinity as your prediction approaches the target value, when training a logistic regression model with a lot of features and thus the possibility to overfit the training data, you can get a gradient that is so large that your model overflows. If you see an error indicating that you divided by zero or a loss of NaN, then most likely this situation has occured. The way to address this problem is to introduce regularization (which you will learn how to do in the next lab). For now, the solution is to reduce the learning rate and/or the number of training steps even if that means that your model is undertrained.**

### Setting Up the Feature Columns and Input Function for TensorFlow
As in the past labs, we define `input_fn` to define a `FeatureColumn` for each categorical and numerical feature, and then define `train_input_fn` to use the training data, `eval_input_fn` to use the validation data, and `test_input_fn` to use the test data.
"""

CATEGORICAL_COLUMNS = ["workclass", "education", "marital_status", "occupation",
                       "relationship", "race", "gender", "native_country"]
NUMERICAL_COLUMNS = ["age", "education_num", "capital_gain", "capital_loss",
                      "hours_per_week"]
LABEL = "income_over_50k"

def input_fn(dataframe):
  """Constructs a dictionary for the feature columns.

  Args:
    dataframe: The Pandas DataFrame to use for the input.
  Returns:
    The feature columns and the associated labels for the provided input.
  """
  # Creates a dictionary mapping each numerical feature column name (k) to
  # the values of that column stored in a constant Tensor.
  numerical_cols = {k: tf.constant(dataframe[k].values) 
                    for k in NUMERICAL_COLUMNS}
  # Creates a dictionary mapping each categorical feature column name (k)
  # to the values of that column stored in a tf.SparseTensor.
  categorical_cols = {k: tf.SparseTensor(
      indices=[[i, 0] for i in range(dataframe[k].size)],
      values=dataframe[k].values,
      dense_shape=[dataframe[k].size, 1])
                      for k in CATEGORICAL_COLUMNS}
  # Merges the two dictionaries into one.
  feature_cols = dict(numerical_cols.items() + categorical_cols.items())
  # Converts the label column into a constant Tensor.
  label = tf.constant(dataframe[LABEL].values)
  # Returns the feature columns and the label.
  return feature_cols, label

def train_input_fn():
  return input_fn(training_examples)

def eval_input_fn():
  return input_fn(validation_examples)

def test_input_fn():
  return input_fn(test_examples)

"""##Prepare Features

Here is a basic implementation of `PrepareFeatures` for you to use.  Feel free to modify this to use feature normalization other than just linear scaling.  

Note that for linear classification with just two labels, the labels must be 0 (think of this as false) and 1 (think of this as true).  Since `income_brackets` is a string, we must convert it to an integer. This can be done using a lambda function that outputs a Boolean  value, and then casts it to an integer. We have provided this for you.
"""

# Linearly rescales to the range [0, 1]
def linear_scale(series):
  min_val = series.min()
  max_val = series.max()
  scale = 1.0 * (max_val - min_val)
  return series.apply(lambda x:((x - min_val) / scale))

def prepare_features(dataframe):
  """Prepares the features for provided dataset.

  Args:
    dataframe: A Pandas DataFrame expected to contain the data.
  Returns:
    A new DataFrame that contains the features to be used for the model.
  """
  processed_features = dataframe.copy()
  for feature in NUMERICAL_COLUMNS:
    processed_features[feature] = linear_scale(dataframe[feature])
    
  # Convert the output target to 0 (for <=50k) and 1 (> 50k)
  processed_features[LABEL] = dataframe["income_bracket"].apply(
      lambda x: ">50K" in x).astype(int)
  
  return processed_features

"""#Divide the provided data for training our model into training and validation sets

As we've done in the past, let's divide the data into a ***training set*** and ***validation set***.  There are 16281 examples so let's set aside 4000 for our validation data.  Let's not forget to randomize the order before splitting the data so that our validation set is a representative sample.
"""

census_df = census_df.reindex(np.random.permutation(census_df.index))
training_examples = prepare_features(census_df.head(12281))
validation_examples = prepare_features(census_df.tail(4000))

"""### Compute Loss

For classification problems, we generally would like our output to be a probability distribution over the possible classes.  When we have two classes the **log loss** is a measure of how close the predicted distribution is to the target distribution, and that is the metric that we will optimize. Again, we use the [sklearn metrics](http://scikit-learn.org/stable/modules/classes.html#module-sklearn.metrics) class.
"""

def compute_loss(model, input_fn, targets):
  """ Computes the log loss for training a linear classifier.
  
  Args:
    model: the trained model to use for making the predictions.
    input_fn: the input_fn to use to make the predicitons.
    targets: a list of the target values being predicted that must be the
             same length as predictions.
    
  Returns:
    The log loss for the provided predictions and targets.
  """      
  
  predictions = np.array(list(model.predict_proba(input_fn=input_fn)))
  return metrics.log_loss(targets, predictions[:, 1])

"""### Train Model

For the most part `define_linear_classifier` is like `define_linear_regressor` with the changes of using the log loss to optimize and the ROC curve to visualize the model quality.  As before we plot a learning curve to see if the model is converging, to help tune the learning rate, and to check if we are overfitting by looking at the loss on the validation data.
"""

def define_linear_classifier(learning_rate):
  """ Defines a linear classifer to predict the target.
  
  Args:
    learning_rate: A `float`, the learning rate.
    
  Returns:
    A linear classifier created with the given parameters.
  """
  linear_classifier = tf.contrib.learn.LinearClassifier(
    feature_columns=construct_feature_columns(),
    optimizer=tf.train.GradientDescentOptimizer(learning_rate=learning_rate),
    gradient_clip_norm=5.0
  )  
  return linear_classifier

def train_model(model, steps):
  """Trains a linear classifier.
  
  Args:
    model: The model to train.
    steps: A non-zero `int`, the total number of training steps.
    
  Returns:
    The trained model.
  """
  # In order to see how the model evolves as we train it, we divide the
  # steps into periods and show the model after each period.
  periods = 10
  steps_per_period = steps / periods
  
  # Train the model, but do so inside a loop so that we can periodically assess
  # loss metrics.  We store the training and validation losses so we can
  # generate a learning curve.
  print "Training model..."
  training_losses = []
  validation_losses = []

  for period in range (0, periods):
    # Call fit to train the model for steps_per_period steps.
    model.fit(input_fn=train_input_fn, steps=steps_per_period)
    
    # Compute the loss between the predictions and the correct labels, append
    # the training and validation loss to the list of losses used to generate
    # the learning curve after training is complete and print the current
    # training loss.
    training_loss = compute_loss(model, train_input_fn,
                                 training_examples[LABEL])
    validation_loss = compute_loss(model, eval_input_fn,
                                   validation_examples[LABEL])
    training_losses.append(training_loss) 
    validation_losses.append(validation_loss) 
    print "  Training loss after period %02d : %0.3f" % (period, training_loss)
      
  # Now that training is done print the final training and validation losses.  
  print "Final Training Loss: %0.3f" % training_loss
  print "Final Validation Loss: %0.3f" % validation_loss 
  
  # Generate a figure with the learning curve on the left and an ROC curve on
  # the right.
  plt.figure(figsize=(10, 5))
  plt.subplot(1, 2, 1)
  plt.title("Learning Curve (Loss vs time)")
  plot_learning_curve(training_losses, validation_losses)
  
  plt.subplot(1, 2, 2)
  plt.tight_layout(pad=1.1, w_pad=3.0, h_pad=3.0) 
  plt.title("ROC Curve on Validation Data")
  validation_probabilities = np.array(list(model.predict_proba(
    input_fn=eval_input_fn)))
  # ROC curve uses the probability that the label is 1.
  make_roc_curve(validation_probabilities[:, 1], validation_examples[LABEL])
   
  return model

"""##Setting up the Features

We will set things up showing you an example of how to set up each of the kind of features you will be using.  Then you can add in additional features.

####Categorical Feauture Columns with known values.

When the values are known you can simply use a line like below.  If you would view the weights, index 0 will be the first key provided, index 1, the next key,.....

```
      gender = tf.contrib.layers.sparse_column_with_keys(column_name="gender", keys=["Female", "Male"])
  
  ```
####Categorical Feature Columns without known values

Since you don't always know the possible values you can instead assign an index to each possible value via hashing where `hash_bucket_size` is the number of hash buckets used.

```
      education = tf.contrib.layers.sparse_column_with_hash_bucket("education", hash_bucket_size=100)
```

####Numerical Feature Columns
As we have seen in past labs, we can directly use numerical features as long as appropriate scaling has been applied. The provided implementation of `prepare_features` linearly scales all numerical featuers to fall in [0,1]
```
   age = tf.contrib.layers.real_valued_column("age") 
```
"""

def construct_feature_columns():
  """Construct TensorFlow Feature Columns for features
  
  Returns:
    A set of feature columns
  """
  
  # Sample of creating a real-valued column.
  age = tf.contrib.layers.real_valued_column("age") 
  
  # Sample of creating a bucketized column using a real-valued column
  boundaries = get_quantile_based_boundaries(training_examples["age"], 5)
  age_buckets = tf.contrib.layers.bucketized_column(age, boundaries)
  
 
  # Sample of creating a categorical column with known values
  gender = tf.contrib.layers.sparse_column_with_keys(
    column_name="gender", keys=["Female", "Male"])
  
  education = tf.contrib.layers.sparse_column_with_hash_bucket(
      "education", hash_bucket_size=50)

  # Sample of a crossed_column which in this case combines a bucketized column
  # and a categorical column. In general, you can include any number of each.
  # So for example you could cross two categorical columns, or two bucketized
  # columns, two categorical columns and also a bucketized column,...
  gender_x_age_buckets = tf.contrib.layers.crossed_column(
      [gender, age_buckets], hash_bucket_size=1000)
  
  
  capital_gain = tf.contrib.layers.real_valued_column("capital_gain")
  
  cap_gain_boundaries = get_quantile_based_boundaries(training_examples["capital_gain"], 100)
  cap_gain_buckets = tf.contrib.layers.bucketized_column(capital_gain, cap_gain_boundaries)
  
  
  capital_loss = tf.contrib.layers.real_valued_column("capital_loss")
  
  cap_loss_boundaries = get_quantile_based_boundaries(training_examples["capital_loss"], 100)
  cap_loss_buckets = tf.contrib.layers.bucketized_column(capital_gain, cap_gain_boundaries)
  
  
  cap_gain_x_cap_loss = tf.contrib.layers.crossed_column(
      [cap_gain_buckets, cap_loss_buckets], hash_bucket_size=1000)

  # In this sample code, note that while the real-valued column age was defined
  # in order to define the bucketized column age_buckets, the real-valued
  # feature age is not being included in feature_columns.  If you would like
  # the real-valued feature age to also be used in training the model then you
  # would add that to the set of feature columns being returned.
  feature_columns=[age_buckets, gender, gender_x_age_buckets, education, cap_gain_x_cap_loss]
  
  return feature_columns

"""### Functions to help visualize our results

Since this is a classification problem, the calibration plot is not a good visualization tool. Instead we use an **ROC curve** in which the x-axis is the false positive rate and the y-axis is the true positive rate.  An ROC curve is a very good way to visualize the quality of a binary classifier and also to pick a threshold when making a binary prediction.  Recall that the line `x=y` corresponds to a random classifier.  **AUC** (the area under the ROC curve) has the nice *probabilistic interpretation that a random positive example is predicted to be more likely to be positive than a random negative example*.

Our implementation of `make_roc_curve` uses the [sklearn metrics](http://scikit-learn.org/stable/modules/classes.html#module-sklearn.metrics) class. There are a lot of tools already available within Python libraries so be sure and look for those.
"""

def make_roc_curve(predictions, targets):
  """ Plots an ROC curve for the provided predictions and targets.

  Args:
    predictions: the probability that the example has label 1.
    targets: a list of the target values being predicted that must be the
             same length as predictions.
  """  
  false_positive_rate, true_positive_rate, thresholds = metrics.roc_curve(
      targets, predictions)
  
  plt.ylabel("true positive rate")
  plt.xlabel("false positive rate")
  plt.plot(false_positive_rate, true_positive_rate)
  
def plot_learning_curve(training_losses, validation_losses):
  """ Plot the learning curve.
  
  Args:
    training_loses: a list of training losses to plot.
    validation_losses: a list of validation losses to plot.
  """        
  plt.ylabel('Loss')
  plt.xlabel('Training Steps')
  plt.plot(training_losses, label="training")
  plt.plot(validation_losses, label="validation")
  plt.legend(loc=1)

"""## Task 1 - Train a Linear Classifier (1/2 point)

Let's start by just training the model with the three features already set-up in `construct_feature_columns`. Without changing anything but the learning_rate and number of steps to train, train the best model you can.
"""

LEARNING_RATE = 0.5
STEPS = 100

linear_classifier = define_linear_classifier(learning_rate = LEARNING_RATE)
linear_classifier = train_model(linear_classifier, steps=STEPS)