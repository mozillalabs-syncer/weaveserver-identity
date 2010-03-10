class WeaveUserException(Exception):

  def __init__(self, value):
    self.value = value

  def __repr__(self):
    return "<WeaveUserException %s>" % self.value

  def __str__(self):
    return self.value
