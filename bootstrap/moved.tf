moved {
  from = aws_iam_role.plan_dev
  to   = aws_iam_role.plan["dev"]
}

moved {
  from = aws_iam_role.plan_prod
  to   = aws_iam_role.plan["prod"]
}

moved {
  from = aws_iam_role.apply_dev
  to   = aws_iam_role.apply["dev"]
}

moved {
  from = aws_iam_role.apply_prod
  to   = aws_iam_role.apply["prod"]
}

moved {
  from = aws_iam_role_policy.plan_dev
  to   = aws_iam_role_policy.plan["dev"]
}

moved {
  from = aws_iam_role_policy.plan_prod
  to   = aws_iam_role_policy.plan["prod"]
}

moved {
  from = aws_iam_role_policy.apply_dev
  to   = aws_iam_role_policy.apply["dev"]
}

moved {
  from = aws_iam_role_policy.apply_prod
  to   = aws_iam_role_policy.apply["prod"]
}
