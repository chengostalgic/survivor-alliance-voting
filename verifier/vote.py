"""Pure validation helpers for the independent tribal verifier."""


def verdict(valid, message, **details):
    return {"valid": valid, "score": 1.0 if valid else 0.0, "message": message, "details": details}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def audit_ballots(ballots, voters, targets):
    require(len(ballots) == len(voters), "wrong number of ballots")
    require({ballot.voter for ballot in ballots} == set(voters), "missing, duplicate, or ineligible voter")
    require(all(ballot.target in targets for ballot in ballots), "ineligible ballot target")
    require(all(ballot.voter != ballot.target for ballot in ballots), "self votes are forbidden")
