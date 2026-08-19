const counters = document.querySelectorAll(".counter");
const observer = new IntersectionObserver((entries) => {
  entries.forEach((entry) => {
    if (entry.isIntersecting) {
      const counter = entry.target;
      const target = +counter.dataset.target;
      let count = 0;
      const updateCounter = () => {
        const increment = target / 50;
        if (count < target) {
          count += increment;
          counter.textContent = Math.ceil(count);
          requestAnimationFrame(updateCounter);
        } else {
          counter.textContent = target + "+";
        }
      };
      updateCounter();
      observer.unobserve(counter);
    }
  });
});

counters.forEach((counter) => {
  observer.observe(counter);
});

const frameworkCards = document.querySelectorAll(".framework-card");
frameworkCards.forEach((card) => {
  card.addEventListener("click", () => {
    card.classList.toggle("active");
  });
});

const reveals = document.querySelectorAll(".reveal");

const observe = new IntersectionObserver(
  (entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        entry.target.classList.add("active");
      }
    });
  },
  {
    threshold: 0.15,
  },
);

reveals.forEach((item) => {
  observe.observe(item);
});
document.addEventListener("DOMContentLoaded", () => {
  const score = document.getElementById("score");
  const circle = document.querySelector(".progress-circle");

  if (!score || !circle) return;

  const radius = circle.r.baseVal.value;
  const circumference = 2 * Math.PI * radius;

  circle.style.strokeDasharray = circumference;
  circle.style.strokeDashoffset = circumference;

  const target = 92;
  let current = 0;

  function animate() {
    current++;

    score.textContent = current;

    const offset = circumference - (current / 100) * circumference;

    circle.style.strokeDashoffset = offset;

    if (current < target) {
      requestAnimationFrame(animate);
    }
  }

  animate();
});
// modal
const modal = document.querySelector(".modal-overlay");
const openBtn = document.querySelector(".Primary");
const closeBtn = document.querySelector(".close-modal");

openBtn.addEventListener("click", () => {
  modal.classList.add("active");
});

closeBtn.addEventListener("click", () => {
  modal.classList.remove("active");
});
modal.addEventListener("click", (e) => {
  if (e.target == modal) {
    modal.classList.remove("active");
  }
});

// step 2 in the modal we have to bring the whole cards
// then we have to choose between these crads
// after we choose one the style will be applied on it
const goalCards = document.querySelectorAll(".goal-card");
goalCards.forEach((card) => {
  card.addEventListener("click", () => {
    goalCards.forEach((item) => {
      item.classList.remove("selected");
    });

    card.classList.add("selected");
  });
});

// how to navigate from step to the other in the modal

const formSteps = document.querySelectorAll(".form-step");
const nextBtn = document.querySelector(".next-btn");
const backBtn = document.querySelector(".back-btn");
// making the progress bar
const progressSteps = document.querySelectorAll(".progress-step");
const progressLines = document.querySelectorAll(".progress-line");

let currentFormStep = 0;

function showStep() {
  formSteps.forEach((step) => {
    step.classList.remove("active");
  });

  formSteps[currentFormStep].classList.add("active");

  // Hide Back button on Step 1
  if (currentFormStep === 0) {
    backBtn.style.visibility = "hidden";
  } else {
    backBtn.style.visibility = "visible";
  }

  // Change button text on the last step
  if (currentFormStep === formSteps.length - 1) {
    nextBtn.textContent = "Generate Report →";
  } else {
    nextBtn.textContent = "Continue →";
  }

  progressSteps.forEach((step, index) => {
    if (index <= currentFormStep) {
      step.classList.add("active");
    } else {
      step.classList.remove("active");
    }
  });
  progressLines.forEach((line, index) => {
    if (index < currentFormStep) {
      line.classList.add("active");
    } else {
      line.classList.remove("active");
    }
  });
}
showStep();

nextBtn.addEventListener("click", () => {
  if (currentFormStep === 1) {
    const selectedGoal = document.querySelector(".goal-card.selected");

    if (!selectedGoal) {
      alert("Please select your primary business goal.");
      return;
    }
  }

  // STEP 3 VALIDATION
  if (currentFormStep === 2) {
    const selectedChallenges = document.querySelectorAll(
      ".challenge-card.selected",
    );

    if (selectedChallenges.length === 0) {
      alert("Please select at least one business challenge.");
      return;
    }
  }

  // STEP 4 VALIDATION
  if (currentFormStep === 3) {
    const selectedStage = document.querySelector(".stage-card.selected");
    if (!selectedStage) {
      alert("Please select your business stage.");
      return;
    }
    // Get Step 1 data
    const businessName = document.getElementById("businessName").value;
    const websiteUrl = document.getElementById("websiteUrl").value;
    const industry = document.getElementById("industry").value;
    // Get Step 2 selected goal
    const selectedGoal = document.querySelector(".goal-card.selected");
    // Get Step 3 selected challenges
    const selectedChallenges = document.querySelectorAll(
      ".challenge-card.selected",
    );
    // Create an array for the challenges
    const challenges = [];
    selectedChallenges.forEach((challenge) => {
      challenges.push(challenge.dataset.value);
    });
    // Put everything into one object
    const auditData = {
      businessName: businessName,
      websiteUrl: websiteUrl,
      industry: industry,
      goal: selectedGoal.dataset.value,
      challenges: challenges,
      stage: selectedStage.dataset.value,
    };
    console.log(auditData);
    return;
  }
  if (currentFormStep < formSteps.length - 1) {
    currentFormStep++;

    showStep();
  }
});

backBtn.addEventListener("click", () => {
  if (currentFormStep > 0) {
    currentFormStep--;

    showStep();
  }
});

// step 3
const challengeCards = document.querySelectorAll(".challenge-card");

challengeCards.forEach((card) => {
  card.addEventListener("click", () => {
    card.classList.toggle("selected");
  });
});

// select from the step 4
const stageCards = document.querySelectorAll(".stage-card");

stageCards.forEach((card) => {
  card.addEventListener("click", () => {
    // Remove selection from all stage cards
    stageCards.forEach((item) => {
      item.classList.remove("selected");
    });

    // Select the clicked card
    card.classList.add("selected");
  });
});
