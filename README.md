<!-- https://github.com/othneildrew/Best-README-Template -->
<a name="readme-top"></a>
<!-- PROJECT SHIELDS -->
<!--
*** I'm using markdown "reference style" links for readability.
*** Reference links are enclosed in brackets [ ] instead of parentheses ( ).
*** See the bottom of this document for the declaration of the reference variables
*** for contributors-url, forks-url, etc. This is an optional, concise syntax you may use.
*** https://www.markdownguide.org/basic-syntax/#reference-style-links
-->

[![MIT License][license-shield]][license-url]


<!-- TABLE OF CONTENTS -->
<details>
  <summary>Table of Contents</summary>
  <ol>
    <li>
      <a href="#about-the-project">About The Project</a>
      <ul>
        <li><a href="#built-with">Built With</a></li>
      </ul>
    </li>
    <li>
      <a href="#getting-started">Getting Started</a>
      <ul>
        <li><a href="#prerequisites">Prerequisites</a></li>
        <li><a href="#installation">Installation</a></li>
      </ul>
    </li>
    <li><a href="#usage">Usage</a></li>
    <li><a href="#roadmap">Roadmap</a></li>
    <li><a href="#contributing">Contributing</a></li>
    <li><a href="#license">License</a></li>
    <li><a href="#contact">Contact</a></li>
    <li><a href="#acknowledgments">Acknowledgments</a></li>
  </ol>
</details>



<!-- ABOUT THE PROJECT -->
## About The Project

<div align="center">
  <img src="images/rasaX_welcome.jpg" alt="Logo" width="620" height="450">
</div>
<!--[![Product Name Screen Shot][product-screenshot]](https://example.com) -->



<p align="right">(<a href="#readme-top">back to top</a>)</p>



### Built and Deployed With

 - Rasa: [Rasa Docs](https://rasa.com/docs/rasa/)
 - Rasa X | Rasa Enterprise: [Rasa X Installation Guide](https://rasa.com/docs/rasa-enterprise/installation-and-setup/install/helm-chart-installation/installation)

<p align="right">(<a href="#readme-top">back to top</a>)</p>

### Enhanced With

* [Skills from Lightcast](https://skills.lightcast.io/)
* [Rapid fuzzy string matching](https://github.com/maxbachmann/RapidFuzz)



<!-- GETTING STARTED -->
## Getting Started

To get a local copy of the _survey chatbot prototype_ up and running follow these steps:

### Installation & Deployment

_Below you can find instructions on installing and setting up the prototype locally (communicate with the chatbot via the CLI)._

1. Get an account and API Key at [https://openai.com/](https://openai.com/)
2. Clone the repo
   ```sh
   git clone https://github.com/Maximilian-Ka/survey-chatbot-prototype.git
   ```
3. Create and activate a virtual Python environment.
4. Install the required packages (this might take a while): 
    ```sh
    pip install -r /actions/requirements.txt
    ```
5. Enter your OpenAi API key in `actions/NLG/.env`
    ```py
    OPENAI_API_KEY=<your_API_key>
    ```
6. Train the chatbot model
    ```sh
    rasa train --augmentation 0
    ```
7. Run the survey chatbot in the CLI.
    ```sh
    rasa shell
    ```
8. and don't forget to run the action server in a separate terminal.
    ```sh
    rasa run actions
    ```

_To deploy the chatbot on a virtual machine using Rasa X, do the following._

_----Coming soon -----_

<p align="right">(<a href="#readme-top">back to top</a>)</p>



<!-- USAGE EXAMPLES -->
<!--## Usage -->

<!--Use this space to show useful examples of how a project can be used. Additional screenshots, code examples and demos work well in this space. You may also link to more resources.

_For more examples, please refer to the [Documentation](https://example.com)_

<p align="right">(<a href="#readme-top">back to top</a>)</p> -->



<!-- ROADMAP -->




<!-- CONTRIBUTING -->
<!--## Contributing -->


<!--<p align="right">(<a href="#readme-top">back to top</a>)</p> -->



<!-- LICENSE -->
## License

Distributed under the MIT License. See `LICENSE.txt` for more information.

<p align="right">(<a href="#readme-top">back to top</a>)</p>



<!-- CONTACT -->
## Contact

<!-- Your Name - [@your_twitter](https://twitter.com/your_username) - email@example.com -->

Project Link: [https://github.com/Maximilian-Ka/survey-chatbot-prototype](https://github.com/Maximilian-Ka/survey-chatbot-prototype)

<p align="right">(<a href="#readme-top">back to top</a>)</p>



<!-- ACKNOWLEDGMENTS -->
## Acknowledgments

<!-- Use this space to list resources you find helpful and would like to give credit to. I've included a few of my favorites to kick things off! -->



<p align="right">(<a href="#readme-top">back to top</a>)</p>



<!-- MARKDOWN LINKS & IMAGES -->
<!-- https://www.markdownguide.org/basic-syntax/#reference-style-links -->

[license-shield]: https://img.shields.io/github/license/othneildrew/Best-README-Template.svg?style=for-the-badge
[license-url]: https://github.com/othneildrew/Best-README-Template/blob/master/LICENSE.txt