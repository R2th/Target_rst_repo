# GrandFinal Round - Data migration

# Task 2: Write a GitHub action run consistency check.

## Evaluation

> [✔] GitHub action pipeline check for mandatory attributes

> [✔] Consistency check for Accepted status

> [✔] Clean code

## Installation

### 1. Add all file workflow definitions in `.github/workflows`:

> `lintrst.yaml`

```yaml
name: Lint

on: [workflow_call]

jobs:
  doctor-rst:
    name: DOCtor-RST
    runs-on: ubuntu-latest
    steps:
      - name: "Checkout code"
        uses: actions/checkout@v2

      - name: DOCtor-RST
        uses: docker://oskarstark/doctor-rst
        with:
          args: --short --error-format=github
        env:
          DOCS_DIR: "docs/"
```

> `validate.yaml`

```yaml
name: Validate
on:
  push:
    paths:
      - "**.rst"
jobs:
  doctorst:
    uses: ./.github/workflows/lintrst.yaml
  validate:
    needs: ["doctorst"]
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v3
      - name: Install dependencies
        run: |
          pip install actions-toolkit xmltodict
          pip install -r requirements.txt
      - name: Build XML
        run: |
          sphinx-build docs _xml_build -b xml
      - name: Run consistency check
        run: |
          python validate.py -i docs/src -xml _xml_build
```

![4d8af2e497f297b2a1c35b7f13b9e5b7.png](https://imgtr.ee/images/2023/06/29/4d8af2e497f297b2a1c35b7f13b9e5b7.png)

![77d064b0b7d203059b8de98022c4f091.png](https://imgtr.ee/images/2023/06/29/77d064b0b7d203059b8de98022c4f091.png)

> `deploy.yaml`

```yaml
name: Deploy
on:
  workflow_run:
    workflows: ["Validate"]
    types:
      - completed
permissions:
  contents: write
jobs:
  deploy:
    if: ${{ github.event.workflow_run.conclusion == 'success' }}
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v3
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
      - name: Sphinx build
        run: |
          sphinx-build docs _build
      - name: Deploy
        uses: peaceiris/actions-gh-pages@v3
        if: ${{ github.event_name == 'push' && github.ref == 'refs/heads/main' }}
        with:
          publish_branch: gh-pages
          github_token: ${{ secrets.GITHUB_TOKEN }}
          publish_dir: _build/
          force_orphan: true
```

> `noti.yaml`

```yaml
name: Notification
on:
  workflow_run:
    workflows: ["Validate", "Deploy"]
    types:
      - completed
jobs:
  notification:
    runs-on: ubuntu-latest
    steps:
      - name: Send mail
        uses: dawidd6/action-send-mail@v2
        with:
          server_address: smtp.gmail.com
          server_port: 465
          username: ${{ secrets.EMAIL_USERNAME }}
          password: ${{ secrets.EMAIL_PASSWORD }}
          subject: "[Notification] Workflow ${{ github.event.workflow_run.name }} in ${{ github.repository }} has ${{ github.event.workflow_run.conclusion }}"
          body: Workflow ${{ github.event.workflow_run.name }} of ${{ github.repository }} has ${{ github.event.workflow_run.conclusion }}
          to: haupro186@gmail.com,minhlam2102002@gmail.com,nq23092016@gmail.com
          from: TheThree - ${{ github.repository }}
```

![1308afd5522cc0fcc0945adc1c0b296e.png](https://imgtr.ee/images/2023/06/29/1308afd5522cc0fcc0945adc1c0b296e.png)

### 2. Creating `secrets` fields for the repository

- You must have add the `EMAIL_USERNAME` and `EMAIL_PASSWORD`
- You can following this [documentation](https://docs.github.com/en/actions/security-guides/encrypted-secrets#creating-encrypted-secrets-for-a-repository)

### 3. Turn on the `Github Pages` feature

- Already described in the previous round.

### 4. Turn on `Protected the branch` feature

- You can following this [documentation](https://cityofaustin.github.io/ctm-dev-workflow/protected-branches.html)
- Here we want to protect the branch `main` and select `Require status checks to pass before merging` with `Status checks that are required.` is `validate` from Github Action

![image](https://imgtr.ee/images/2023/06/29/064801c031f5c62e7b8f32dccf21efa1.png)

### 5. Turn on automatic merge pull request

- You can following this [documentation](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/configuring-pull-request-merges/managing-auto-merge-for-pull-requests-in-your-repository)

![9fc1968a67aa1f7ffd7799a9e191b581.png](https://imgtr.ee/images/2023/06/29/9fc1968a67aa1f7ffd7799a9e191b581.png)

## Overview Github action pipeline

- Following the pipeline was designed below. If any workflow error occurs like `DOCtorst`, `Validate`, the next one will be ignored or skipped. And after that if will trigger to the workflow `Notifications` to send the workflow status notification by email.

![image](https://imgtr.ee/images/2023/06/29/9fec4fa81bd31a62e146c5c2d5f8029a.png)

The pipeline will be executed when the repository have any change like `push`, `pull_request` with file `.rst`.

### 1. DOCtorst

- Using like as consistency to documentation, easy add more rule like check grammar of the documentation
- You can find the documentation of the DOCtorst here: [DOCtorst](https://github.com/OskarStark/doctor-rst)
- You should add file `.doctor-rst.yaml` to the folder you want to check consistency

  ```yaml
  rules:
  american_english: ~
  ```

### 2. Validate

#### a. Option 1: Use `sphinx-needs` to parse `rst` to `xml`

- After run DOCtorst check grammar of the documentation, we next to need check rules which need to be applied:
- The rules said:

  - The `status`, `crq`, `verification criteria` and `safety_level` attributes are `mandatory and cannot be empty.
  - If the `status` is `"Accepted"`, the `allocation` attribute is mandatory.

- Because content in the first `.rst` not be readable by any library of Python and it not be accessible. So we need the temporary content file which export easiest from `.rst` folder and easily for readability. We choose to convert to a temporary file `.xml` by `sphinx` and `sphinx-needs`.

  ```bash
  sphinx-build docs _xml_build -b xml
  ```

- After build `.xml` successfully which store in folder `_xml_build`, we read the content by `xmltodict` and parse the information needed to validate the rules.

  ```bash
  ╰─ python validate.py -h
  usage: validate.py [-h] [-i INPUTS] [-xml XML_OUTPUT]

  options:
  -h, --help            show this help message and exit
  -i INPUTS, --inputs INPUTS
                          Path to the folder containing all the rst files
  -xml XML_OUTPUT, --xml_output XML_OUTPUT
                          Path to output after run sphinx builder xml
  ```

  ```bash
  python validate.py -i docs/src -xml _xml_build
  ```

- If any error is encountered. We will using `actions_toolkit` to exit code execution when it is running in workflow and using the format message below.

  ```bash
  <Module path>
      <Requirement ID> - <Requirement Type>
          ERROR: field '<attribute Name>' must be filled
          …..
  <Module 2 path>
      <Requirement ID> - <Requirement Type>
      ERROR: field '<attribute Name>' must be filled
  ```

- Example:

  ```bash
  Error: docs/src/ECU_Requirement.rst
      sw_req - 629014
          ERROR:field 'safety_level' must be filled
          ERROR:field 'crq' must be filled
  Error: docs/src/Test_2.rst
      sys_req - 222225
          ERROR:field 'verify' must be filled
      sw_req - 222226
          ERROR:field 'allocation' must be filled
          ERROR:field 'verify' must be filled
  Error: Process completed with exit code 1.
  ```

#### b. Option 2: Use Regular Expression to validate (Optional)

- Besides parsing to XML format which is readable, we also adapt another method, which is using RegEx pattern matching to retrieve `rst` content and validate its consistency.
- Note that this solution is just a side-solution and is not as effective as the Option 1. For more detail, please refer the source code at the [regex_validate.py](./regex_validate.py)

### 3. Deploy

- Already explain in the previous round

## Output

### 1. Check consistency before `pull_request`

> Success
> ![8c9cfdc575f41f620c4ff75519e2db32.png](https://imgtr.ee/images/2023/06/29/8c9cfdc575f41f620c4ff75519e2db32.png)

> Failed
> ![b2dfeebd22b3c674c393750d5eb1f668.png](https://imgtr.ee/images/2023/06/29/b2dfeebd22b3c674c393750d5eb1f668.png)

<div style="page-break-after: always;"></div>

### 2. Notifications to the email

[![c03b50a5642971418ca5858762dcc89d.md.jpeg](https://imgtr.ee/images/2023/06/29/c03b50a5642971418ca5858762dcc89d.md.jpeg)](https://imgtr.ee/image/357542591-1969188456769049-2388862340658717146-n.KZSA)
